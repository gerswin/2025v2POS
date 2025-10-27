"""
Management command to show cache statistics and health information.
Useful for monitoring cache performance and debugging issues.
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from venezuelan_pos.apps.sales.cache import sales_cache


class Command(BaseCommand):
    help = 'Show cache statistics and health information'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output statistics in JSON format'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed Redis information'
        )
    
    def handle(self, *args, **options):
        try:
            # Get cache health data
            health_data = sales_cache.health_check()
            
            if options['json']:
                # Output as JSON
                self.stdout.write(json.dumps(health_data, indent=2))
                return
            
            # Human-readable output
            self.stdout.write(self.style.SUCCESS("=== Cache Health Status ==="))
            self.stdout.write(f"Status: {health_data.get('status', 'unknown')}")
            self.stdout.write(f"Response Time: {health_data.get('response_time_ms', 0):.2f}ms")
            self.stdout.write(f"Redis Client Available: {health_data.get('redis_client_available', False)}")
            self.stdout.write(f"Timestamp: {health_data.get('timestamp', 'unknown')}")
            
            # Show operation results
            operations = health_data.get('operations', {})
            if operations:
                self.stdout.write("\n=== Cache Operations ===")
                for op, success in operations.items():
                    status_icon = "✓" if success else "✗"
                    self.stdout.write(f"{status_icon} {op.capitalize()}: {'Success' if success else 'Failed'}")
            
            # Show detailed Redis info if available and requested
            if options['detailed'] and sales_cache._redis_client:
                try:
                    redis_info = sales_cache._redis_client.info()
                    
                    self.stdout.write("\n=== Redis Information ===")
                    self.stdout.write(f"Version: {redis_info.get('redis_version', 'unknown')}")
                    self.stdout.write(f"Mode: {redis_info.get('redis_mode', 'unknown')}")
                    self.stdout.write(f"Connected Clients: {redis_info.get('connected_clients', 0)}")
                    self.stdout.write(f"Used Memory: {redis_info.get('used_memory_human', 'unknown')}")
                    self.stdout.write(f"Max Memory: {redis_info.get('maxmemory_human', 'unlimited')}")
                    
                    # Calculate and show hit rate
                    hits = redis_info.get('keyspace_hits', 0)
                    misses = redis_info.get('keyspace_misses', 0)
                    total = hits + misses
                    hit_rate = (hits / total * 100) if total > 0 else 0
                    
                    self.stdout.write(f"\n=== Performance Metrics ===")
                    self.stdout.write(f"Keyspace Hits: {hits:,}")
                    self.stdout.write(f"Keyspace Misses: {misses:,}")
                    self.stdout.write(f"Hit Rate: {hit_rate:.2f}%")
                    self.stdout.write(f"Total Commands: {redis_info.get('total_commands_processed', 0):,}")
                    
                    # Show keyspace info
                    keyspace_info = {}
                    for key, value in redis_info.items():
                        if key.startswith('db'):
                            keyspace_info[key] = value
                    
                    if keyspace_info:
                        self.stdout.write(f"\n=== Keyspace Information ===")
                        for db, info in keyspace_info.items():
                            self.stdout.write(f"{db}: {info}")
                    
                    # Show memory usage breakdown
                    memory_info = {
                        'used_memory': redis_info.get('used_memory', 0),
                        'used_memory_rss': redis_info.get('used_memory_rss', 0),
                        'used_memory_peak': redis_info.get('used_memory_peak', 0),
                        'used_memory_lua': redis_info.get('used_memory_lua', 0),
                    }
                    
                    self.stdout.write(f"\n=== Memory Usage ===")
                    for metric, value in memory_info.items():
                        if value:
                            # Convert bytes to human readable
                            if value > 1024 * 1024:
                                readable = f"{value / (1024 * 1024):.2f} MB"
                            elif value > 1024:
                                readable = f"{value / 1024:.2f} KB"
                            else:
                                readable = f"{value} bytes"
                            
                            self.stdout.write(f"{metric.replace('_', ' ').title()}: {readable}")
                    
                except Exception as redis_error:
                    self.stdout.write(
                        self.style.WARNING(f"\nFailed to get detailed Redis info: {redis_error}")
                    )
            
            # Show error if cache is unhealthy
            if health_data.get('status') != 'healthy':
                error_msg = health_data.get('error', 'Unknown error')
                self.stdout.write(
                    self.style.ERROR(f"\n⚠️  Cache is unhealthy: {error_msg}")
                )
                
                # Suggest troubleshooting steps
                self.stdout.write("\n=== Troubleshooting Suggestions ===")
                self.stdout.write("1. Check if Redis server is running")
                self.stdout.write("2. Verify Redis connection settings in Django settings")
                self.stdout.write("3. Check Redis server logs for errors")
                self.stdout.write("4. Test Redis connection manually: redis-cli ping")
            
        except Exception as e:
            raise CommandError(f"Failed to get cache statistics: {e}")