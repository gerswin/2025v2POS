"""
Management command to clear sales caches.
Useful for debugging and forcing cache rebuilds.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from venezuelan_pos.apps.sales.cache import sales_cache


class Command(BaseCommand):
    help = 'Clear sales caches'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm cache clearing (required for safety)'
        )
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Show cache statistics before clearing'
        )
    
    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    "This will clear all sales caches and may impact performance.\n"
                    "Use --confirm to proceed."
                )
            )
            return
        
        start_time = timezone.now()
        
        try:
            # Show stats before clearing if requested
            if options['stats']:
                self.stdout.write("Cache statistics before clearing:")
                health_data = sales_cache.health_check()
                self.stdout.write(f"  Status: {health_data.get('status', 'unknown')}")
                self.stdout.write(f"  Response time: {health_data.get('response_time_ms', 0):.2f}ms")
                
                if 'redis_info' in health_data:
                    redis_info = health_data['redis_info']
                    self.stdout.write(f"  Memory used: {redis_info.get('used_memory_human', 'unknown')}")
                    self.stdout.write(f"  Hit rate: {redis_info.get('hit_rate_percent', 0):.2f}%")
                
                self.stdout.write("")
            
            # Clear all caches
            self.stdout.write("Clearing all sales caches...")
            
            success = sales_cache.clear_all_caches()
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS("Successfully cleared all sales caches")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("Cache clearing completed with some errors")
                )
            
            # Show execution time
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            self.stdout.write(f"Cache clearing completed in {duration:.2f} seconds")
            
            # Recommend warming caches
            self.stdout.write(
                self.style.WARNING(
                    "\nRecommendation: Run 'python manage.py warm_caches --all-active' "
                    "to restore performance for active events."
                )
            )
            
        except Exception as e:
            raise CommandError(f"Cache clearing failed: {e}")