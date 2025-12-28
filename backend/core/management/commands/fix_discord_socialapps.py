"""
Management command to fix Discord SocialApp configuration conflicts.

This project uses SETTINGS-BASED configuration for Discord OAuth (configured in
backend/backend/settings/base.py via SOCIALACCOUNT_PROVIDERS).

This command removes ALL SocialApp entries for Discord from the database to
prevent conflicts. django-allauth should be configured in ONLY ONE place:
- ✅ This project uses: Settings-based (SOCIALACCOUNT_PROVIDERS['discord']['APP'])
- ❌ NOT database-based (SocialApp model entries)

If you have SocialApp entries in the database, this command will remove them
to ensure only settings-based configuration is used. This fixes the
MultipleObjectsReturned error that occurs when both exist simultaneously.

See DISCORD_SETUP.md for full documentation.
"""
from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialApp
from django.conf import settings


class Command(BaseCommand):
    help = 'Remove Discord SocialApp entries from database when using settings-based configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete all Discord SocialApp entries even if settings are not configured',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        
        # Check if settings-based configuration exists
        has_settings_config = (
            hasattr(settings, 'SOCIALACCOUNT_PROVIDERS') and
            'discord' in settings.SOCIALACCOUNT_PROVIDERS and
            'APP' in settings.SOCIALACCOUNT_PROVIDERS['discord'] and
            settings.SOCIALACCOUNT_PROVIDERS['discord']['APP'].get('client_id')
        )
        
        # Get all Discord SocialApps
        discord_apps = SocialApp.objects.filter(provider='discord')
        app_count = discord_apps.count()
        
        if app_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No Discord SocialApp entries found in database. Nothing to fix.')
            )
            return
        
        self.stdout.write(f'Found {app_count} Discord SocialApp entry/entries in database.')
        
        if has_settings_config:
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  WARNING: Discord is configured in settings (SOCIALACCOUNT_PROVIDERS).\n'
                    'Having both settings-based AND database-based configuration causes conflicts.\n'
                    'All database entries will be removed to use settings-based configuration only.'
                )
            )
        elif not force:
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  WARNING: No settings-based configuration found.\n'
                    'If you want to use database-based configuration, keep these entries.\n'
                    'If you want to remove them anyway, use --force flag.'
                )
            )
            return
        
        # Delete all Discord SocialApp entries
        deleted_ids = []
        for app in discord_apps:
            deleted_ids.append(app.id)
            if dry_run:
                site_info = f" (sites: {', '.join(str(s.id) for s in app.sites.all())})" if app.sites.exists() else " (no sites)"
                self.stdout.write(f'  [DRY RUN] Would delete SocialApp ID: {app.id}{site_info}')
            else:
                site_info = f" (sites: {', '.join(str(s.id) for s in app.sites.all())})" if app.sites.exists() else " (no sites)"
                app.delete()
                self.stdout.write(f'  ✓ Deleted SocialApp ID: {app.id}{site_info}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[DRY RUN] Would delete {len(deleted_ids)} SocialApp entr{"y" if len(deleted_ids) == 1 else "ies"}.'
                )
            )
            self.stdout.write('Run without --dry-run to actually delete them.')
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ Successfully removed {len(deleted_ids)} Discord SocialApp entr{"y" if len(deleted_ids) == 1 else "ies"} from database.'
                )
            )
            if has_settings_config:
                self.stdout.write(
                    self.style.SUCCESS(
                        'Discord OAuth will now use settings-based configuration only.'
                    )
                )

