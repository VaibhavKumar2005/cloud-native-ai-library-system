"""
Django Management Command: Run VeriRAG Benchmarks
Usage: python manage.py run_benchmarks [--output benchmark_results.json]
"""

from django.core.management.base import BaseCommand, CommandError
from ai_engine.benchmarks import VeriRAGBenchmark, HALLUCINATION_TEST_CASES
from ai_engine.rag_logic import get_verified_answer
import json


class Command(BaseCommand):
    help = 'Run VeriRAG hallucination prevention benchmarks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='benchmark_results.json',
            help='Output file path for benchmark results'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            default=1,
            help='User ID for multi-tenant testing'
        )
        parser.add_argument(
            '--quick',
            action='store_true',
            help='Run quick subset of tests (first 3)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🧪 Starting VeriRAG Benchmark Suite'))
        self.stdout.write('-' * 50)
        
        try:
            benchmark = VeriRAGBenchmark(rag_function=get_verified_answer)
            
            # Select test cases
            test_cases = HALLUCINATION_TEST_CASES
            if options['quick']:
                test_cases = test_cases[:3]
                self.stdout.write(self.style.WARNING('Running quick mode (3 tests)'))
            
            # Run suite
            suite = benchmark.run_suite(
                test_cases=test_cases,
                user_id=options['user_id']
            )
            
            # Print report
            benchmark.print_report(suite)
            
            # Export results
            benchmark.export_results(options['output'], suite)
            
            # Summary
            if suite.passed_tests == suite.total_tests:
                self.stdout.write(self.style.SUCCESS(
                    f'✅ All {suite.total_tests} tests passed!'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'⚠️ {suite.passed_tests}/{suite.total_tests} tests passed'
                ))
            
            self.stdout.write(self.style.SUCCESS(
                f'📊 Results saved to: {options["output"]}'
            ))
            
        except Exception as e:
            raise CommandError(f'Benchmark failed: {str(e)}')
