from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.core.files.storage import default_storage
from django.core.files import File
from django.core.exceptions import ValidationError
from django.http import FileResponse
import io
from django.db.models import Q
from django.db import transaction
from django.conf import settings

from ensembles.models import Arrangement, Ensemble, ArrangementVersion, EnsembleUsership, PartAsset, PartName, Commit
from ensembles.serializers import (
    EnsembleSerializer,
    ArrangementSerializer,
    ArrangementVersionSerializer,
    ArrangementVersionFromCommitSerializer,
    CreateArrangementCommitSerializer,
    EnsemblePartNameMergeSerializer,
    CreateArrangementVersionMsczSerializer
)
from django.db.models.expressions import RawSQL

from ensembles.tasks import export_arrangement_version, prep_and_export_mscz
from ensembles.tasks.part_books import generate_books_for_ensemble

from scoreforge.cli import mscz_to_json
import tempfile
from pathlib import Path
import hashlib

from ensembles.git import (
    ArrangementGitError,
    GitAuthor,
    commit_canonical_snapshot,
    init_repo,
    materialize_commit_mscz_to_version,
)
from ensembles.git.materialize import build_mscz_bytes_from_commit


class EnsembleViewSet(viewsets.ModelViewSet):
    serializer_class = EnsembleSerializer
    lookup_field = "slug"  # use slug instead of pk
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter ensembles to only those the user has access to"""
        user = self.request.user
        if not user.is_authenticated:
            return Ensemble.objects.none()
        
        # Get ensembles where user is owner or has usership
        return Ensemble.objects.filter(
            Q(owner=user) | Q(userships__user=user)
        ).distinct()

    def perform_create(self, serializer):
        """Set the owner when creating an ensemble"""
        serializer.save(owner=self.request.user)
        EnsembleUsership.objects.create(
            ensemble=serializer.instance,
            user=self.request.user,
            role=EnsembleUsership.Role.ADMIN,
        )

    @action(detail=True, methods=["get"], url_path="arrangements")
    def arrangements(self, request, slug=None):
        """Return all arrangements for a specific ensemble."""
        ensemble = self.get_object()
        # Verify user has access
        if not self._has_access(ensemble, request.user):
            return Response(
                {"detail": "You do not have access to this ensemble."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        arrangements = (
            ensemble.arrangements
            .annotate(
                first_num=RawSQL(
                    "CAST((regexp_matches(mvt_no, '^([0-9]+)'))[1] AS INTEGER)",
                    []
                ),
                second_num=RawSQL(
                    "CAST((regexp_matches(mvt_no, '^[0-9]+(?:-|m)([0-9]+)'))[1] AS INTEGER)",
                    []
                ),
            )
            .order_by("first_num", "second_num", "mvt_no")
        )
        serializer = ArrangementSerializer(arrangements, many=True)
        return Response(serializer.data)

    def _has_access(self, ensemble, user):
        """Check if user has access to ensemble"""
        return ensemble.owner == user or EnsembleUsership.objects.filter(
            ensemble=ensemble, user=user
        ).exists()

    @action(detail=True, methods=["get", "post"], url_path="invite-link")
    def invite_link(self, request, slug=None):
        """Generate or retrieve the invite link for an ensemble"""
        ensemble = self.get_object()
        user = request.user
        
        # Check if user is owner or has admin role
        is_owner = ensemble.owner == user
        is_admin = user.get_ensemble_role(ensemble) == EnsembleUsership.Role.ADMIN
        
        if not is_owner and not is_admin:
            return Response(
                    {"detail": "Only ensemble owners and admins can generate invite links."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Generate token if it doesn't exist
        token = ensemble.get_or_create_invite_token()
        
        # Build the join URL using frontend URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        join_url = f"{frontend_url.rstrip('/')}/join/{token}"
        
        return Response({
            "invite_token": token,
            "join_url": join_url,
            "ensemble_name": ensemble.name,
            "ensemble_slug": ensemble.slug,
        })
    
    @action(detail=True, methods=["post"], url_path="remove-user")
    def remove_user(self, request, slug=None):
        """Remove a user from the ensemble using their user ID"""
        ensemble = self.get_object()
        user = request.user

        if user.is_ensemble_admin(ensemble) is False:
            return Response(
                    {"detail": "Only admins can remove users."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        #TODO[SC-278]: Move this to a serializer
        user_id = request.data.get("user_id")
        if not user_id:
            return Response(
                {"detail": "User ID is required to remove a user."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            usership = EnsembleUsership.objects.get(ensemble=ensemble, user__id=user_id)
            usership.delete()
            return Response(
                {"detail": "User removed from ensemble."},
                status=status.HTTP_200_OK
            )
        except EnsembleUsership.DoesNotExist:
            return Response(
                {"detail": "User is not a member of this ensemble."},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=["post"], url_path="change-user-role")
    def change_user_role(self, request, slug=None):
        """Change a user's role in the ensemble"""
        ensemble = self.get_object()
        user = request.user

        if user.get_ensemble_role(ensemble) != EnsembleUsership.Role.ADMIN:
            return Response(
                    {"detail": "Only admins can change user roles."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        user_id = request.data.get("user_id")
        new_role = request.data.get("role")
        
        if not user_id:
            return Response(
                {"detail": "User ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not new_role:
            return Response(
                {"detail": "Role is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate role
        valid_roles = [choice[0] for choice in EnsembleUsership.Role.choices]
        if new_role not in valid_roles:
            return Response(
                {"detail": f"Invalid role. Must be one of: {', '.join(valid_roles)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            usership = EnsembleUsership.objects.get(ensemble=ensemble, user__id=user_id)
            usership.role = new_role
            usership.save(update_fields=['role'])
            return Response(
                {"detail": "User role updated successfully.", "role": usership.role},
                status=status.HTTP_200_OK
            )
        except EnsembleUsership.DoesNotExist:
            return Response(
                {"detail": "User is not a member of this ensemble."},
                status=status.HTTP_404_NOT_FOUND
            )
        

    @action(detail=True, methods=["post"])
    def merge_part_names(self, request, slug=None):
        serializer = EnsemblePartNameMergeSerializer(data=request.data, context={"ensemble": self.get_object()})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        first = validated_data["first_part"]
        second = validated_data["second_part"]

        try:
            merged = PartName.merge_part_names(
                first, second, validated_data.get("new_displayname", "") or ""
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"id": merged.id, "display_name": merged.display_name},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def generate_part_books(self, request, slug=None):
        ensemble = self.get_object()

        generate_books_for_ensemble.delay(ensemble.id)
        return Response({"detail": "Export of Part Books triggered"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="update-part-order")
    def update_part_order(self, request, slug=None):
        """Update the order of parts for an ensemble. Only admins can do this."""
        ensemble = self.get_object()
        user = request.user

        if not user.is_ensemble_admin(ensemble):
            return Response(
                {"detail": "Only ensemble admins can update part order."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Expected format: {"part_orders": [{"id": 1, "order": 0}, {"id": 2, "order": 1}, ...]}
        part_orders = request.data.get("part_orders", [])
        
        if not isinstance(part_orders, list):
            return Response(
                {"detail": "part_orders must be a list of objects with 'id' and 'order' fields."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate that all part IDs belong to this ensemble
        part_ids = [item.get("id") for item in part_orders if item.get("id")]
        if not part_ids:
            return Response(
                {"detail": "No part IDs provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        parts = PartName.objects.filter(id__in=part_ids, ensemble=ensemble)
        if parts.count() != len(part_ids):
            return Response(
                {"detail": "One or more part IDs are invalid or do not belong to this ensemble."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update orders
        part_dict = {item.get("id"): item.get("order") for item in part_orders if item.get("id") is not None}
        for part in parts:
            if part.id in part_dict:
                part.order = part_dict[part.id]
                part.save(update_fields=["order"])

        return Response(
            {"detail": "Part order updated successfully."},
            status=status.HTTP_200_OK
        )


class BaseArrangementViewSet(viewsets.ModelViewSet):
    serializer_class = ArrangementSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter arrangements to only those in ensembles the user has access to"""
        user = self.request.user
        if not user.is_authenticated:
            return Arrangement.objects.none()
        
        # Get arrangements from ensembles where user is owner or has usership
        return Arrangement.objects.filter(
            Q(ensemble__owner=user) | Q(ensemble__userships__user=user)
        ).distinct()

    def perform_create(self, serializer):
        """Verify user has access to the ensemble before creating arrangement"""
        ensemble = serializer.validated_data['ensemble']
        user = self.request.user
        
        if ensemble.owner != user and not EnsembleUsership.objects.filter(
            ensemble=ensemble, user=user
        ).exists():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have access to this ensemble.")
        
        serializer.save()

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, *args, **kwargs):
        """Return all versions for an arrangement"""
        arr = self.get_object()
        versions = arr.versions.all()
        serializer = ArrangementVersionSerializer(versions, many=True)
        return Response(serializer.data)


class ArrangementViewSet(BaseArrangementViewSet):
    # TODO: Is this even used anywhere?
    lookup_field = "slug"


class ArrangementByIdViewSet(BaseArrangementViewSet):
    lookup_field = "id"

    @action(detail=True, methods=["get"], url_path="commits")
    def commits(self, request, id=None, *args, **kwargs):
        arrangement = self.get_object()

        # Versions created from commits: prefer FK; legacy rows used commit-<sha>.mscz filenames.
        version_commit_shas = set()
        for v in ArrangementVersion.objects.filter(arrangement=arrangement, commit__isnull=False).select_related("commit"):
            version_commit_shas.add(v.commit.sha)

        commit_rows = (
            Commit.objects.filter(git_repo__arrangement=arrangement)
            .order_by("-committed_at")
            .values(
                "id",
                "sha",
                "message",
                "author_name",
                "author_email",
                "authored_at",
                "committed_at",
                "parent_sha",
                "tag",
                "created_by_id",
            )[:30]
        )

        return Response(
            [
                {
                    **row,
                    "has_version": row["sha"] in version_commit_shas,
                }
                for row in commit_rows
            ]
        )

    @action(detail=True, methods=["get"], url_path="download_latest_commit_mscz")
    def download_latest_commit_mscz(self, request, id=None, *args, **kwargs):
        """Build and download MSCZ from the latest git commit for this arrangement (not tied to a version)."""
        arrangement = self.get_object()

        latest = (
            Commit.objects.filter(git_repo__arrangement=arrangement)
            .order_by("-committed_at")
            .first()
        )
        if latest is None:
            return Response(
                {"detail": "No commits for this arrangement yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            mscz_bytes = build_mscz_bytes_from_commit(
                arrangement=arrangement, commit_sha=latest.sha
            )
        except ArrangementGitError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {"detail": f"Failed to build MSCZ: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        filename = f"{arrangement.title}-commit-{latest.sha[:8]}.mscz"
        return FileResponse(
            io.BytesIO(mscz_bytes),
            as_attachment=True,
            filename=filename,
            content_type="application/octet-stream",
        )

    @action(detail=True, methods=["post"], url_path="new-commit")
    def new_commit(self, request, id=None, *args, **kwargs):
        # This endpoint is invoked via `arrangements-by-id/<id>/new-commit/`.
        # We load the arrangement directly by id (so "exists but excluded from
        # the user-filtered queryset" doesn't turn into a 404).
        #TODO: Serializer here
        arrangement = Arrangement.objects.filter(id=id).first()
        if arrangement is None:
            return Response(
                {"detail": "Arrangement not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Explicit access check to return a clearer 403 vs a misleading 404.
        user = request.user
        if not (
            arrangement.ensemble.owner == user
            or EnsembleUsership.objects.filter(ensemble=arrangement.ensemble, user=user).exists()
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You do not have access to this ensemble.")

        serializer = CreateArrangementCommitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded = serializer.validated_data["file"]
        message = (serializer.validated_data.get("message") or "").strip()
        if not message:
            message = f"{arrangement.slug} new commit"

        # Repo is normally created when Arrangement is created (signal/backfill),
        # but we still ensure it exists here for robustness.
        try:
            init_repo(arrangement)
        except ArrangementGitError as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        with tempfile.TemporaryDirectory(prefix="arr_new_commit_") as tmp:
            tmp_dir = Path(tmp)
            in_path = tmp_dir / "input.mscz"
            out_dir = tmp_dir / "canonical"
            out_dir.mkdir(parents=True, exist_ok=True)

            # Save upload to disk
            content = b"".join(chunk for chunk in uploaded.chunks())
            in_path.write_bytes(content)

            # Canonicalize via scoreforge
            mscz_to_json(str(in_path), str(out_dir), "canonical")
            canonical_json = out_dir / "canonical.json"

            tree_hash = hashlib.sha256(canonical_json.read_bytes()).hexdigest()

            payload_dir = tmp_dir / "commit_payload"
            payload_dir.mkdir(parents=True, exist_ok=True)
            (payload_dir / "canonical.json").write_bytes(canonical_json.read_bytes())
            canonical_template = out_dir / "canonical.mscz"
            if canonical_template.is_file():
                (payload_dir / "canonical.mscz").write_bytes(canonical_template.read_bytes())
            (payload_dir / ".gitattributes").write_text(
                "canonical.json merge=scoreforge\n",
                encoding="utf-8",
            )

            user = request.user
            author = GitAuthor(
                name=(user.get_full_name() or user.username or "User"),
                email=(user.email or "user@divisi.local"),
            )

            try:
                commit_row = commit_canonical_snapshot(
                    arrangement,
                    payload_dir,
                    author=author,
                    message=message,
                    created_by=user,
                )
            except ArrangementGitError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {
                #TODO: Commit Serializer
                "commit": {
                    "id": commit_row.id,
                    "sha": commit_row.sha,
                    "message": commit_row.message,
                    "author_name": commit_row.author_name,
                    "author_email": commit_row.author_email,
                    "authored_at": commit_row.authored_at,
                    "committed_at": commit_row.committed_at,
                    "parent_sha": commit_row.parent_sha,
                    "tag": commit_row.tag,
                    "created_by": commit_row.created_by_id,
                },
                "canonical_tree_hash": tree_hash,
            },
            status=status.HTTP_201_CREATED,
        )


class ArrangementVersionViewSet(viewsets.ModelViewSet):
    serializer_class = ArrangementVersionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter versions to only those in ensembles the user has access to"""
        user = self.request.user
        if not user.is_authenticated:
            return ArrangementVersion.objects.none()
        
        # Get versions from arrangements in ensembles where user is owner or has usership
        return ArrangementVersion.objects.filter(
            Q(arrangement__ensemble__owner=user) | Q(arrangement__ensemble__userships__user=user)
        ).distinct()
    

    @action(detail=False, methods=["post"])
    def create_from_commit(self, request):
        serializer = ArrangementVersionFromCommitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        accessible_arrangements = Arrangement.objects.filter(
            Q(ensemble__owner=request.user) | Q(ensemble__userships__user=request.user)
        ).distinct()


        commit_hash = data.get("commit_hash")
        commit_obj = (
            Commit.objects.filter(
                sha=commit_hash,
                git_repo__arrangement__in=accessible_arrangements,
            )
            .select_related("git_repo__arrangement")
            .first()
        )
        if commit_obj is None:
            return Response(
                {"detail": "Commit not found or inaccessible."},
                status=status.HTTP_404_NOT_FOUND,
            )

        arrangement = commit_obj.git_repo.arrangement
        file_name = f"{arrangement.title}-{commit_obj.sha}.mscz"

        try:
            with transaction.atomic():
                version = ArrangementVersion(
                    arrangement=arrangement,
                    file_name=file_name,
                    num_measures_per_line_score=data.get(
                        "num_measures_per_line_score", 8
                    ),
                    num_measures_per_line_part=data.get(
                        "num_measures_per_line_part", 6
                    ),
                    num_lines_per_page=data.get("num_lines_per_page", 8),
                    commit=commit_obj
                )
                version.save(version_type=data.get("version_type", "patch"))
        except Exception as e:
            return Response(
                {"detail": f"Failed to create arrangement version from commit: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # try:
        materialize_commit_mscz_to_version(
            arrangement=arrangement,
            commit_sha=commit_obj.sha,
            version=version,
        )
        
        #TODO: Add this back eventually, we have sentry so we can catch errors easier now
        # except Exception as e:
        #     version.is_processing = False
        #     version.error_on_export = True
        #     version.save(update_fields=["is_processing", "error_on_export"])
        #     return Response(
        #         {"detail": f"Failed to materialize raw mscz from commit: {e}"},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )

        prep_and_export_mscz.delay(version.pk)

        return Response(
            {
                "message": "Arrangement version created from commit.",
                "version_id": version.id,
                "version_label": version.version_label,
                "arrangement_id": arrangement.id,
                "commit_sha": commit_obj.sha,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="upload")
    def upload_arrangement_version(self, request):
        serializer = CreateArrangementVersionMsczSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        res = serializer.save()
        if "error" in res.keys():
            return Response(
                {"message": "Error", "details": res["error"]}
            )

        return Response(
            {"message": "File Uploaded Successfully", "version_id": res["version_id"]},
            status=status.HTTP_202_ACCEPTED,
        )


    #TODO[SC-278]: Make this have a serializer omg
    @action(detail=True, methods=["get"])
    def get_download_links(self, request, pk=None):
        version = self.get_object()

        latest_commit_mscz_path = (
            f"/api/arrangements-by-id/{version.arrangement_id}/download_latest_commit_mscz/"
        )
        response_data = {
            "message": "Successfully created download links",
            "is_processing": version.is_processing,
            "error": version.error_on_export,
            "raw_mscz_url": request.build_absolute_uri(latest_commit_mscz_path),
            "processed_mscz_url": request.build_absolute_uri(version.output_file_url),
            "score_parts_pdf_link": None,  # Will be set from Part model or old file
            "score_pdf_url": None,  # Individual score PDF
            "mp3_link": request.build_absolute_uri(version.audio_file_url),
            "parts": []  # List of individual part URLs
        }

        # Latest-commit MSCZ is built on demand from git; require at least one commit
        if not Commit.objects.filter(git_repo__arrangement_id=version.arrangement_id).exists():
            response_data["raw_mscz_url"] = None

        if not default_storage.exists(version.output_file_key):
            response_data["processed_mscz_url"] = None

        # Get score and parts from Part model (new way)
        parts = PartAsset.objects.filter(arrangement_version=version)
        if parts.exists():
            for part in parts:
                if default_storage.exists(part.file_key):
                    part_data = {
                        "id": part.id,
                        "name": part.name,
                        "is_score": part.is_score,
                        "file_url": request.build_absolute_uri(part.file_url),
                        "download_url": request.build_absolute_uri(
                            f"/api/arrangementversions/{version.id}/download_part/{part.id}/"
                        ),
                    }
                    response_data["parts"].append(part_data)
                    
                    # Set score PDF URL if this is the score
                    if part.is_score:
                        response_data["score_pdf_url"] = part_data["file_url"]
                        # Also set score_parts_pdf_link for backward compatibility
                        response_data["score_parts_pdf_link"] = part_data["file_url"]
        else:
            # Fallback to old combined PDF file if no parts exist
            if default_storage.exists(version.score_parts_pdf_key):
                response_data["score_parts_pdf_link"] = request.build_absolute_uri(
                    version.score_parts_pdf_url
                )
            # Also check for individual score PDF (old format)
            elif default_storage.exists(version.score_pdf_key):
                response_data["score_pdf_url"] = request.build_absolute_uri(version.score_pdf_url)
                response_data["score_parts_pdf_link"] = request.build_absolute_uri(version.score_pdf_url)

        return Response(response_data)

    @action(detail=True, methods=["post"])
    def trigger_audio_export(self, request, pk=None):
        version = self.get_object()
        
        match version.audio_state:
            case ArrangementVersion.AudioStatus.NONE:
                # Trigger export
                version.audio_state = ArrangementVersion.AudioStatus.PROCESSING
                version.save(update_fields=["audio_state"])
                export_arrangement_version.delay(version.id, action="mp3")
                return Response({}, status=status.HTTP_202_ACCEPTED)
            case ArrangementVersion.AudioStatus.PROCESSING:
                return Response({}, status=status.HTTP_102_PROCESSING)
            case ArrangementVersion.AudioStatus.COMPLETE:
                return Response({"mp3_link": request.build_absolute_uri(version.audio_file_url)})
            case ArrangementVersion.AudioStatus.ERROR:
                return Response({"error": "Error on export of audio file"}, status=500)
    
    @action(detail=True, methods=["get"])
    def list_parts(self, request, pk=None):
        """List all individual parts (including score) for this arrangement version"""
        version = self.get_object()
        
        parts = PartAsset.objects.filter(arrangement_version=version)
        
        parts_data = []
        for part in parts:
            parts_data.append({
                "id": part.id,
                "name": part.name,
                "is_score": part.is_score,
                "file_url": request.build_absolute_uri(part.file_url),
                "download_url": request.build_absolute_uri(
                    f"/api/arrangementversions/{version.id}/download_part/{part.id}/"
                ),
            })
        
        return Response({
            "version_id": version.id,
            "parts": parts_data,
            "count": len(parts_data),
        })
    
    @action(detail=True, methods=["get"], url_path="download_part/(?P<part_id>[^/.]+)")
    def download_part(self, request, pk=None, part_id=None):
        """Download a specific part PDF"""
        version = self.get_object()
        
        try:
            part = PartAsset.objects.get(id=part_id, arrangement_version=version)
        except PartAsset.DoesNotExist:
            return Response(
                {"detail": "Part not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not default_storage.exists(part.file_key):
            return Response(
                {"detail": "Part PDF file not found in storage"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return redirect to the file URL
        file_url = default_storage.url(part.file_key)
        return Response({
            "file_url": request.build_absolute_uri(file_url),
            "redirect": file_url,
        })
    



class JoinEnsembleView(APIView):
    """View to join an ensemble using an invite token"""
    permission_classes = [AllowAny]  # Default to allow any, check auth in methods
    
    def post(self, request, *args, **kwargs):
        # Require authentication for POST
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required to join an ensemble."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        token = request.data.get('token') or kwargs.get('token')
        
        if not token:
            return Response(
                {"detail": "Invite token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            ensemble = Ensemble.objects.get(invite_token=token)
        except Ensemble.DoesNotExist:
            return Response(
                {"detail": "Invalid invite token."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user = request.user
        
        # Check if user already has access
        if ensemble.owner == user:
            return Response(
                {
                    "detail": "You are already the owner of this ensemble.",
                    "ensemble": {
                        "id": ensemble.id,
                        "name": ensemble.name,
                        "slug": ensemble.slug,
                    }
                },
                status=status.HTTP_200_OK
            )
        
        if EnsembleUsership.objects.filter(ensemble=ensemble, user=user).exists():
            return Response(
                {
                    "detail": "You are already a member of this ensemble.",
                    "ensemble": {
                        "id": ensemble.id,
                        "name": ensemble.name,
                        "slug": ensemble.slug,
                    }
                },
                status=status.HTTP_200_OK
            )
        
        # Create the usership
        EnsembleUsership.objects.create(ensemble=ensemble, user=user)
        
        return Response(
            {
                "detail": "Successfully joined the ensemble.",
                "ensemble": {
                    "id": ensemble.id,
                    "name": ensemble.name,
                    "slug": ensemble.slug,
                }
            },
            status=status.HTTP_201_CREATED
        )
    
    def get(self, request, *args, **kwargs):
        """Get ensemble info from token without joining (for preview)"""
        token = request.query_params.get('token') or kwargs.get('token')
        
        if not token:
            return Response(
                {"detail": "Invite token is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            ensemble = Ensemble.objects.get(invite_token=token)
        except Ensemble.DoesNotExist:
            return Response(
                {"detail": "Invalid invite token."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Return ensemble info (user doesn't need to be authenticated for this)
        return Response({
            "ensemble": {
                "id": ensemble.id,
                "name": ensemble.name,
                "slug": ensemble.slug,
            },
            "is_authenticated": request.user.is_authenticated,
            "already_member": (
                request.user.is_authenticated and (
                    ensemble.owner == request.user or
                    EnsembleUsership.objects.filter(ensemble=ensemble, user=request.user).exists()
                )
            ) if request.user.is_authenticated else False,
        })
