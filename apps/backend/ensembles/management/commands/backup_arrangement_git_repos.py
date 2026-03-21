import datetime as dt
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from ensembles.models import Arrangement
from ensembles.git import ArrangementGitError, init_repo, run_git


class Command(BaseCommand):
    help = "Create git bundle backups for arrangement repos and upload to object storage."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Log actions without writing bundles.")
        parser.add_argument("--arrangement-id", type=int, default=None, help="Only process a single arrangement id.")
        parser.add_argument(
            "--storage-prefix",
            type=str,
            default="arrangement-git-bundles/",
            help="Storage key prefix to upload bundles under.",
        )
        parser.add_argument(
            "--gc",
            action="store_true",
            help="Run 'git gc' on each repo before bundling (can be slow).",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        arrangement_id: int | None = options["arrangement_id"]
        storage_prefix: str = options["storage_prefix"]
        run_gc: bool = options["gc"]

        qs = Arrangement.objects.all().order_by("id")
        if arrangement_id is not None:
            qs = qs.filter(id=arrangement_id)

        ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        for arrangement in qs.iterator():
            try:
                repo_path = Path(init_repo(arrangement))
                if run_gc and not dry_run:
                    run_git(["--git-dir", str(repo_path), "gc"])

                bundle_name = f"arr_{arrangement.id}_{ts}.bundle"
                storage_key = f"{storage_prefix.rstrip('/')}/{bundle_name}"

                self.stdout.write(f"[BUNDLE] {arrangement.id}/{arrangement.slug} -> {storage_key}")
                if dry_run:
                    continue

                with tempfile.TemporaryDirectory(prefix="arr_git_bundle_") as tmp:
                    bundle_path = Path(tmp) / bundle_name
                    run_git(["--git-dir", str(repo_path), "bundle", "create", str(bundle_path), "--all"])
                    default_storage.save(storage_key, ContentFile(bundle_path.read_bytes()))

            except (ArrangementGitError, Exception) as e:
                raise RuntimeError(f"Failed to bundle arrangement {arrangement.id}: {e}") from e

