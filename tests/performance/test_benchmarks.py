"""Performance benchmark tests for fast-intercom-mcp."""

import time

import pytest


class TestPerformanceBenchmarks:
    """Basic performance benchmark tests."""

    def test_import_speed(self, benchmark):
        """Benchmark the import speed of the main module."""

        def import_module():
            import fast_intercom_mcp

            return fast_intercom_mcp

        result = benchmark(import_module)
        assert result is not None

    def test_basic_operation_speed(self, benchmark):
        """Benchmark a basic operation."""

        def basic_operation():
            # Placeholder for actual performance test
            time.sleep(0.001)  # Simulate some work
            return sum(range(1000))

        result = benchmark(basic_operation)
        assert result == 499500

    @pytest.mark.benchmark(group="database")
    def test_database_connection_speed(self, benchmark):
        """Benchmark database connection speed."""

        def connect_db():
            # Placeholder for database connection benchmark
            time.sleep(0.01)  # Simulate connection time
            return True

        result = benchmark(connect_db)
        assert result is True
