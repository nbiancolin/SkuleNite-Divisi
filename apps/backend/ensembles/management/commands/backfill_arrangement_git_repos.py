import hashlib
import tempfile
from logging import getLogger
from pathlib import Path

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from ensembles.models import Arrangement, ArrangementVersion
from ensembles.services.arrangement_git import GitAuthor, init_repo, commit_canonical_snapshot, tag_version

from scoreforge.cli import mscz_to_json


logger = getLogger("export_tasks")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class Command(BaseCommand):
    help = "Backfill per-arrangement git repos and persist ArrangementVersion git_commit_sha."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Compute and log work without writing.")
        parser.add_argument("--arrangement-id", type=int, default=None, help="Only process a single arrangement id.")
        parser.add_argument("--limit", type=int, default=None, help="Maximum number of versions to backfill.")
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continue processing other versions when one fails.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        arrangement_id: int | None = options["arrangement_id"]
        limit: int | None = options["limit"]
        continue_on_error: bool = options["continue_on_error"]

        qs = Arrangement.objects.all().order_by("id")
        if arrangement_id is not None:
            qs = qs.filter(id=arrangement_id)

        processed = 0
        for arrangement in qs.iterator():
            try:
                if not dry_run:
                    init_repo(arrangement)
            except Exception as e:
                msg = f"[BACKFILL] Failed to init repo for arrangement {arrangement.id}: {e}"
                if continue_on_error:
                    self.stderr.write(self.style.ERROR(msg))
                    continue
                raise

            versions = (
                ArrangementVersion.objects.filter(arrangement=arrangement)
                .order_by("timestamp", "id")
                .only("id", "version_label", "timestamp", "file_name", "git_commit_sha", "git_tag", "canonical_tree_hash")
            )

            for version in versions.iterator():
                if limit is not None and processed >= limit:
                    self.stdout.write(self.style.SUCCESS(f"Reached --limit={limit}, stopping."))
                    return

                if version.git_commit_sha:
                    continue

                input_key = version.mscz_file_key
                if not default_storage.exists(input_key):
                    input_key = version.output_file_key

                if not default_storage.exists(input_key):
                    msg = f"[BACKFILL] Missing storage object for version {version.id} ({arrangement.slug} v{version.version_label})"
                    if continue_on_error:
                        self.stderr.write(self.style.ERROR(msg))
                        continue
                    raise RuntimeError(msg)

                try:
                    with tempfile.TemporaryDirectory(prefix="arr_backfill_") as tmp:
                        tmp_dir = Path(tmp)
                        in_path = tmp_dir / "input.mscz"
                        out_dir = tmp_dir / "canonical"
                        out_dir.mkdir(parents=True, exist_ok=True)

                        with default_storage.open(input_key, "rb") as src:
                            in_path.write_bytes(src.read())

                        mscz_to_json(str(in_path), str(out_dir), "canonical")
                        canonical_json = out_dir / "canonical.json"
                        tree_hash = _sha256_file(canonical_json)

                        payload_dir = tmp_dir / "commit_payload"
                        payload_dir.mkdir(parents=True, exist_ok=True)
                        (payload_dir / "canonical.json").write_bytes(canonical_json.read_bytes())
                        canonical_template = out_dir / "canonical.mscz"
                        if canonical_template.is_file():
                            (payload_dir / "canonical.mscz").write_bytes(
                                canonical_template.read_bytes()
                            )
                        (payload_dir / ".gitattributes").write_text(
                            "canonical.json merge=scoreforge\n",
                            encoding="utf-8",
                        )

                        sha = "DRY_RUN"
                        tag = f"v{version.version_label}"
                        if not dry_run:
                            author = GitAuthor(name="Divisi System", email="system@divisi.local")
                            msg = f"{arrangement.slug} v{version.version_label}"
                            sha = commit_canonical_snapshot(
                                arrangement,
                                payload_dir,
                                author=author,
                                timestamp=version.timestamp,
                                message=msg,
                            )
                            tag_version(arrangement, sha, tag)

                            with transaction.atomic():
                                v = ArrangementVersion.objects.select_for_update().get(id=version.id)
                                if v.git_commit_sha:
                                    continue
                                v.git_commit_sha = sha
                                v.git_tag = tag
                                v.canonical_tree_hash = tree_hash
                                v.save(update_fields=["git_commit_sha", "git_tag", "canonical_tree_hash"])

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"[BACKFILL] {arrangement.id}/{arrangement.slug} v{version.version_label} -> {sha} ({tag})"
                            )
                        )
                        processed += 1

                except Exception as e:
                    msg = f"[BACKFILL] Failed for version {version.id} ({arrangement.slug} v{version.version_label}): {e}"
                    if continue_on_error:
                        self.stderr.write(self.style.ERROR(msg))
                        continue
                    raise

