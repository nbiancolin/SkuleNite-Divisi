from django.core.management.base import BaseCommand

from ensembles.models import Arrangement
from ensembles.git import init_repo


class Command(BaseCommand):
    help = "Initialize empty per-arrangement bare git repos for all existing arrangements."

    def add_arguments(self, parser):
        parser.add_argument("--arrangement-id", type=int, default=None, help="Only process a single arrangement id.")
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continue processing other arrangements when one fails.",
        )

    def handle(self, *args, **options):
        arrangement_id: int | None = options["arrangement_id"]
        continue_on_error: bool = options["continue_on_error"]

        qs = Arrangement.objects.all().order_by("id")
        if arrangement_id is not None:
            qs = qs.filter(id=arrangement_id)

        for arrangement in qs.iterator():
            try:
                path = init_repo(arrangement)
                self.stdout.write(self.style.SUCCESS(f"[INIT] {arrangement.id}/{arrangement.slug} -> {path}"))
            except Exception as e:
                msg = f"[INIT] Failed for arrangement {arrangement.id}/{arrangement.slug}: {e}"
                if continue_on_error:
                    self.stderr.write(self.style.ERROR(msg))
                    continue
                raise

