import io
from django.core.files.storage import default_storage
from rest_framework import serializers

from ensembles.models import (
    Arrangement,
    UserScoreVersion,
)
from ensembles.serializers.arrangement_version import ArrangementVersionSerializer


class ArrangementSerializer(serializers.ModelSerializer):
    latest_version = ArrangementVersionSerializer(read_only=True)
    latest_version_num = serializers.ReadOnlyField()
    has_unversioned_latest_commit = serializers.SerializerMethodField()
    has_unresolved_comments_on_latest_version = serializers.SerializerMethodField()

    class Meta:
        model = Arrangement
        fields = [
            "id",
            "ensemble",
            "ensemble_name",
            "ensemble_slug",
            "title",
            "slug",
            "subtitle",
            "composer",
            "mvt_no",
            "style",
            "latest_version",
            "latest_version_num",
            "has_unversioned_latest_commit",
            "has_unresolved_comments_on_latest_version",
        ]
        read_only_fields = [
            "slug",
            "ensemble_name",
            "ensemble_slug",
        ]

    def get_has_unversioned_latest_commit(self, obj) -> bool:
        annotated = getattr(obj, "_has_unversioned_latest_commit", None)
        if annotated is not None:
            return bool(annotated)
        return obj.has_unversioned_latest_commit

    def get_has_unresolved_comments_on_latest_version(self, obj) -> bool:
        annotated = getattr(obj, "_has_unresolved_comments_on_latest_version", None)
        if annotated is not None:
            return bool(annotated)
        return obj.has_unresolved_comments_on_latest_version


class CreateArrangementCommitSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=False)
    message = serializers.CharField(required=False)
    force = serializers.BooleanField(required=False)

    def save(self, **kwargs):
        assert self.validated_data, "must call is_valid first"

        from ensembles.models.commit import Commit

        arr = self.context["arrangement"]
        user = self.context["user"]

        user_is_up_to_date = UserScoreVersion.user_is_up_to_date(
            user=user, arrangement=arr
        )
        # Need to get head commit early so the head isnt the new commit ...
        head_commit = Commit.latest_for_arrangement(arr)

        latest = Commit.latest_for_arrangement(arr)
        force = self.validated_data.get("force", False)
        if latest and latest.is_merge_conflict and not force:
            return {"client_error": "Must use force when resolving a merge conflict"}

        if not user_is_up_to_date and not force:
            try:
                base_commit = UserScoreVersion.objects.get(
                    user=user, arrangement=arr
                ).commit
            except UserScoreVersion.DoesNotExist:
                base_commit = None
            if base_commit is None or not default_storage.exists(
                base_commit.mscz_file_key
            ):
                return {
                    "client_error": "Download the latest score before uploading your changes.",
                }

        new_commit = Commit.create_new_commit(
            arrangement=arr,
            created_by_user=self.context["user"],
            create_kwargs={
                "file_name": self.validated_data["file"].name,
                "message": self.validated_data.get(
                    "message", f"New commit for {arr.title}"
                ),
            },
        )

        uploaded_file = self.validated_data["file"]

        # Save file to storage using the storage key
        try:
            # Create a file-like object from the uploaded file
            file_content = b""
            for chunk in uploaded_file.chunks():
                file_content += chunk

            # Save to storage using the key
            default_storage.save(new_commit.mscz_file_key, io.BytesIO(file_content))
            logger.info(f"Saved file to storage: {new_commit.mscz_file_key}")

        except Exception as e:
            logger.error(f"Failed to save file to storage: {e}")
            # Clean up the version if file save failed
            new_commit.delete()
            return {"error": "Failed to save file to storage"}

        if user_is_up_to_date or force:
            # Direct tip commit (no auto-merge); user is aligned with their upload.
            UserScoreVersion.record_for_user(user, arr, new_commit)
            return {"status": "ok", "commit": new_commit}

        else:
            # Need to 3 way merge scores and create merge conflict
            base_commit = UserScoreVersion.objects.get(
                user=self.context["user"], arrangement=arr
            ).commit
            user_commit = new_commit

            MERGE_FILE_NAME = new_commit.file_name[:-4] + "merge.mscz"

            final_commit = Commit.create_new_commit(
                arr,
                self.context["user"],
                create_kwargs={
                    "is_merge_commit": True,
                    "file_name": MERGE_FILE_NAME,
                    "message": f"Merge commit generated by Divisi btwn commits b:{base_commit.id}, h:{head_commit.id}, u:{user_commit.id}",
                },
            )

            def download_file(in_key, output_file_name, temp_dir) -> str:
                temp_input = os.path.join(temp_dir, output_file_name)
                with (
                    default_storage.open(in_key, "rb") as src,
                    open(temp_input, "wb") as dst,
                ):
                    dst.write(src.read())
                return temp_input

            import os
            import tempfile

            from django.core.files.base import ContentFile
            from musescore_score_diff.merge import (
                MergeConflictException,
                three_way_merge_mscz,
            )

            merge_error_response = {
                "merge_error": "Unable to merge scores. Use a force commit",
            }

            def fail_complicated_merge(exc: BaseException | None = None):
                if exc is not None:
                    logger.exception("Score merge failed: %s", exc)
                if final_commit.pk:
                    final_commit.delete()
                user_commit.delete()
                return merge_error_response

            def save_merged_output_to_final_commit():
                final_commit.file_name = user_commit.file_name
                with open(output_path, "rb") as f:
                    default_storage.save(
                        final_commit.mscz_file_key, ContentFile(f.read())
                    )
                final_commit.save()

            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    base_path = download_file(
                        base_commit.mscz_file_key, "base.mscz", temp_dir
                    )
                    head_path = download_file(
                        head_commit.mscz_file_key, "head.mscz", temp_dir
                    )
                    user_path = download_file(
                        user_commit.mscz_file_key, "user.mscz", temp_dir
                    )
                    output_path = os.path.join(temp_dir, "output.mscz")

                    try:
                        # TODO run this in celery bc this can take a long time
                        three_way_merge_mscz(
                            base_path, head_path, user_path, output_path
                        )
                        save_merged_output_to_final_commit()
                    except MergeConflictException:
                        try:
                            final_commit.is_merge_conflict = True
                            save_merged_output_to_final_commit()
                        except Exception as exc:
                            return fail_complicated_merge(exc)
                    except Exception as exc:
                        return fail_complicated_merge(exc)
            except Exception as exc:
                return fail_complicated_merge(exc)

            # Merge commit or conflict: user must download and resolve before USV advances.
            return {"status": "ok", "commit": final_commit}
