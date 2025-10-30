from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "Run a backfill function by its name"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("Function Name", type=str, nargs="+")

    def handle(self, *args, **kwargs):
        assert hasattr(f"utils.scripts.{args[1]}", args[1]), (
            "NO backfill function found with that name. Ensure the file and function are named the same"
        )
        #call provided fn
        getattr(f"utils.scripts.{args[1]}", args[1])()
