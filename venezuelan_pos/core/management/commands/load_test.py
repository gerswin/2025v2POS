"""
Management command to run load tests against the Venezuelan POS system.
"""

import time
import threading
import statistics
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from venezuelan_pos.apps.tenants.models import Tenant

User = get_user_model()


class Command(BaseCommand):
    help = 'Run load tests against the Venezuelan POS system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--concurrent-users',
            type=int,
            default=10,
            help='Number of concurrent users to simulate'
        )
        parser.add_argument(
            '--requests-per-user',
            type=int,
            default=50,
            help='Number of requests each user should make'
        )
        parser.add_argument(
            '--target-url',
            type=str,
            default='http://localhost:8000',
            help='Target URL for load testing'
        )
        parser.add_argument(
            '--test-type',
            choices=['api', 'web', 'mixed'],
            default='mixed',
            help='Type of load test to run'
        )
    
    def handle(self, *args, **options):
        self.concurrent_users = options['concurrent_users']
        self.requests_per_user = options['requests_per_user']
        self.target_url = options['target_url']
        self.test_type = options['test_type']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting load test with {self.concurrent_users} concurrent users, '
                f'{self.requests_per_user} requests per user...'
            )
        )
        
        # Run load test
        results = self.run_load_test()
        
        # Display results
        self.display_results(results)
    
    def run_load_test(self):
        """Run the load test with concurrent users."""
        results = {
            'response_times': [],
            'status_codes': {},
            'errors': [],
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
        }
        
        start_time = time.time()
        
        # Create thread pool for concurrent users
        with ThreadPoolExecutor(max_workers=self.concurrent_users) as executor:
            # Submit tasks for each user
            futures = []
            for user_id in range(self.concurrent_users):
                future = executor.submit(self.simulate_user, user_id)
                futures.append(future)
            
            # Collect results from all users
            for future in as_completed(futures):
                try:
                    user_results = future.result()
                    
                    # Aggregate results
                    results['response_times'].extend(user_results['response_times'])
                    results['total_requests'] += user_results['total_requests']
                    results['successful_requests'] += user_results['successful_requests']
                    results['failed_requests'] += user_results['failed_requests']
                    results['errors'].extend(user_results['errors'])
                    
                    # Aggregate status codes
                    for code, count in user_results['status_codes'].items():
                        results['status_codes'][code] = results['status_codes'].get(code, 0) + count
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'User simulation failed: {str(e)}')
                    )
        
        total_time = time.time() - start_time
        results['total_time'] = total_time
        results['requests_per_second'] = results['total_requests'] / total_time if total_time > 0 else 0
        
        return results
    
    def simulate_user(self, user_id):
        """Simulate a single user making requests."""
        user_results = {
            'response_times': [],
            'status_codes': {},
            'errors': [],
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
        }
        
        # Create session for this user
        session = requests.Session()
        
        for request_num in range(self.requests_per_user):
            try:
                # Choose endpoint based on test type
                endpoint = self.choose_endpoint(request_num)
                
                start_time = time.time()
                response = session.get(f"{self.target_url}{endpoint}")
                response_time = time.time() - start_time
                
                user_results['response_times'].append(response_time)
                user_results['total_requests'] += 1
                
                # Track status codes
                status_code = response.status_code
                user_results['status_codes'][status_code] = (
                    user_results['status_codes'].get(status_code, 0) + 1
                )
                
                if 200 <= status_code < 400:
                    user_results['successful_requests'] += 1
                else:
                    user_results['failed_requests'] += 1
                
                # Small delay between requests
                time.sleep(0.1)
                
            except Exception as e:
                user_results['errors'].append(f"User {user_id}, Request {request_num}: {str(e)}")
                user_results['failed_requests'] += 1
                user_results['total_requests'] += 1
        
        return user_results
    
    def choose_endpoint(self, request_num):
        """Choose an endpoint to test based on the test type and request number."""
        if self.test_type == 'api':
            endpoints = [
                '/api/health/',
                '/api/tenants/',
                '/api/events/',
                '/api/zones/',
                '/api/pricing/stages/',
            ]
        elif self.test_type == 'web':
            endpoints = [
                '/admin/',
                '/events/',
                '/sales/',
                '/reports/',
            ]
        else:  # mixed
            endpoints = [
                '/api/health/',
                '/admin/',
                '/api/events/',
                '/events/',
                '/api/zones/',
                '/sales/',
                '/api/pricing/stages/',
                '/reports/',
            ]
        
        return endpoints[request_num % len(endpoints)]
    
    def display_results(self, results):
        """Display load test results."""
        self.stdout.write(self.style.SUCCESS('\n=== LOAD TEST RESULTS ===\n'))
        
        # Basic statistics
        self.stdout.write(f'Total Requests: {results["total_requests"]}')
        self.stdout.write(f'Successful Requests: {results["successful_requests"]}')
        self.stdout.write(f'Failed Requests: {results["failed_requests"]}')
        self.stdout.write(f'Success Rate: {(results["successful_requests"] / results["total_requests"] * 100):.2f}%')
        self.stdout.write(f'Total Time: {results["total_time"]:.2f} seconds')
        self.stdout.write(f'Requests per Second: {results["requests_per_second"]:.2f}')
        
        # Response time statistics
        if results['response_times']:
            response_times = results['response_times']
            self.stdout.write('\n--- Response Time Statistics ---')
            self.stdout.write(f'Average: {statistics.mean(response_times) * 1000:.2f}ms')
            self.stdout.write(f'Median: {statistics.median(response_times) * 1000:.2f}ms')
            self.stdout.write(f'Min: {min(response_times) * 1000:.2f}ms')
            self.stdout.write(f'Max: {max(response_times) * 1000:.2f}ms')
            
            if len(response_times) >= 20:
                p95 = statistics.quantiles(response_times, n=20)[18] * 1000
                self.stdout.write(f'P95: {p95:.2f}ms')
            
            if len(response_times) >= 100:
                p99 = statistics.quantiles(response_times, n=100)[98] * 1000
                self.stdout.write(f'P99: {p99:.2f}ms')
        
        # Status code distribution
        self.stdout.write('\n--- Status Code Distribution ---')
        for code, count in sorted(results['status_codes'].items()):
            percentage = (count / results['total_requests'] * 100)
            self.stdout.write(f'{code}: {count} ({percentage:.1f}%)')
        
        # Errors
        if results['errors']:
            self.stdout.write(f'\n--- Errors ({len(results["errors"])}) ---')
            for error in results['errors'][:10]:  # Show first 10 errors
                self.stdout.write(f'  {error}')
            
            if len(results['errors']) > 10:
                self.stdout.write(f'  ... and {len(results["errors"]) - 10} more errors')
        
        # Performance assessment
        self.stdout.write('\n--- Performance Assessment ---')
        
        avg_response_time = statistics.mean(results['response_times']) * 1000 if results['response_times'] else 0
        success_rate = (results['successful_requests'] / results['total_requests'] * 100) if results['total_requests'] > 0 else 0
        
        if success_rate < 95:
            self.stdout.write(self.style.ERROR(f'❌ Low success rate: {success_rate:.2f}%'))
        elif success_rate < 99:
            self.stdout.write(self.style.WARNING(f'⚠️  Moderate success rate: {success_rate:.2f}%'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Good success rate: {success_rate:.2f}%'))
        
        if avg_response_time > 1000:
            self.stdout.write(self.style.ERROR(f'❌ High average response time: {avg_response_time:.2f}ms'))
        elif avg_response_time > 500:
            self.stdout.write(self.style.WARNING(f'⚠️  Moderate average response time: {avg_response_time:.2f}ms'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Good average response time: {avg_response_time:.2f}ms'))
        
        if results['requests_per_second'] < 50:
            self.stdout.write(self.style.ERROR(f'❌ Low throughput: {results["requests_per_second"]:.2f} RPS'))
        elif results['requests_per_second'] < 100:
            self.stdout.write(self.style.WARNING(f'⚠️  Moderate throughput: {results["requests_per_second"]:.2f} RPS'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Good throughput: {results["requests_per_second"]:.2f} RPS'))
        
        self.stdout.write(f'\nLoad test completed successfully!')