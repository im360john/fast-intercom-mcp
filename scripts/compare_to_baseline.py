#!/usr/bin/env python3
"""
Compare current performance against recorded baselines
Helps detect performance regressions
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Any

from record_baseline import PerformanceBaseline


class PerformanceComparison:
    """Compare performance metrics against baselines"""

    def __init__(self, baseline_file: str = "performance_baselines.json"):
        self.baseline_runner = PerformanceBaseline(baseline_file)
        self.baselines = self.baseline_runner.baselines

    def get_baseline(self, tag: str) -> dict[str, Any] | None:
        """Get a specific baseline by tag"""
        return self.baselines.get(tag)

    def measure_current_performance(self) -> dict[str, Any]:
        """Measure current performance metrics"""
        print("Measuring current performance...")
        print("=" * 60)

        current = {
            "date": datetime.now().isoformat(),
            "system": self.baseline_runner.get_system_info(),
            "metrics": {},
        }

        # Measure all metrics
        import_metrics = self.baseline_runner.measure_import_performance()
        if import_metrics:
            current["metrics"].update(import_metrics)

        db_metrics = self.baseline_runner.measure_database_performance()
        if db_metrics:
            current["metrics"].update(db_metrics)

        memory_metrics = self.baseline_runner.measure_memory_usage()
        if memory_metrics:
            current["metrics"].update(memory_metrics)

        return current

    def calculate_change(self, baseline_value: float, current_value: float) -> tuple[float, float]:
        """Calculate absolute and percentage change"""
        if baseline_value == 0:
            return current_value, float("inf") if current_value > 0 else 0

        absolute_change = current_value - baseline_value
        percent_change = (absolute_change / baseline_value) * 100

        return absolute_change, percent_change

    def format_change(self, absolute: float, percent: float, lower_is_better: bool = True) -> str:
        """Format change with color coding"""
        # Determine if change is good or bad
        is_improvement = (percent < 0 and lower_is_better) or (percent > 0 and not lower_is_better)

        # Color codes
        if abs(percent) < 5:
            color = ""  # No significant change
        elif is_improvement:
            color = "\033[32m"  # Green for improvement
        else:
            color = "\033[31m"  # Red for regression

        reset = "\033[0m" if color else ""

        # Format string
        sign = "+" if absolute > 0 else ""
        return f"{color}{sign}{absolute:.2f} ({sign}{percent:.1f}%){reset}"

    def compare_metrics(
        self, baseline: dict[str, Any], current: dict[str, Any], threshold: float = 10.0
    ) -> dict[str, Any]:
        """Compare current metrics against baseline"""
        baseline_metrics = baseline.get("metrics", {})
        current_metrics = current.get("metrics", {})

        comparison = {
            "baseline_tag": baseline.get("tag", "unknown"),
            "baseline_date": baseline.get("date", "unknown"),
            "current_date": current.get("date", "unknown"),
            "metrics": {},
            "regressions": [],
            "improvements": [],
        }

        # Define which metrics are "lower is better"
        lower_is_better = {
            "import_time_seconds": True,
            "cli_startup_seconds": True,
            "database_size_mb": True,
            "avg_query_time_ms": True,
            "server_startup_memory_mb": True,
            "sync_duration_seconds": True,
        }

        # Compare each metric
        for metric_name, baseline_value in baseline_metrics.items():
            if metric_name in current_metrics and isinstance(baseline_value, int | float):
                current_value = current_metrics[metric_name]

                if isinstance(current_value, int | float):
                    absolute, percent = self.calculate_change(baseline_value, current_value)

                    lib = lower_is_better.get(metric_name, True)

                    comparison["metrics"][metric_name] = {
                        "baseline": baseline_value,
                        "current": current_value,
                        "absolute_change": absolute,
                        "percent_change": percent,
                        "formatted_change": self.format_change(absolute, percent, lib),
                    }

                    # Track significant changes
                    if abs(percent) > threshold:
                        if (percent > 0 and lib) or (percent < 0 and not lib):
                            comparison["regressions"].append(
                                {
                                    "metric": metric_name,
                                    "percent_change": percent,
                                    "baseline": baseline_value,
                                    "current": current_value,
                                }
                            )
                        else:
                            comparison["improvements"].append(
                                {
                                    "metric": metric_name,
                                    "percent_change": percent,
                                    "baseline": baseline_value,
                                    "current": current_value,
                                }
                            )

        # Handle nested metrics (like query_times_ms)
        if "query_times_ms" in baseline_metrics and "query_times_ms" in current_metrics:
            baseline_queries = baseline_metrics["query_times_ms"]
            current_queries = current_metrics["query_times_ms"]

            comparison["metrics"]["query_times_ms"] = {}

            for query_name, baseline_time in baseline_queries.items():
                if query_name in current_queries:
                    current_time = current_queries[query_name]
                    absolute, percent = self.calculate_change(baseline_time, current_time)

                    comparison["metrics"]["query_times_ms"][query_name] = {
                        "baseline": baseline_time,
                        "current": current_time,
                        "formatted_change": self.format_change(absolute, percent, True),
                    }

        return comparison

    def generate_report(self, comparison: dict[str, Any]) -> None:
        """Generate a formatted comparison report"""
        print("\nPerformance Comparison Report")
        print("=" * 60)
        print(f"Baseline: {comparison['baseline_tag']} ({comparison['baseline_date']})")
        print(f"Current: {comparison['current_date']}")
        print()

        # Summary
        num_regressions = len(comparison["regressions"])
        num_improvements = len(comparison["improvements"])

        if num_regressions == 0 and num_improvements == 0:
            print("✅ No significant performance changes detected")
        else:
            if num_regressions > 0:
                print(f"⚠️  {num_regressions} performance regression(s) detected")
            if num_improvements > 0:
                print(f"✅ {num_improvements} performance improvement(s) detected")

        print("\nDetailed Metrics:")
        print("-" * 60)

        # Display metrics
        for metric_name, data in comparison["metrics"].items():
            if metric_name == "query_times_ms":
                print("\nQuery Performance (ms):")
                for query_name, query_data in data.items():
                    print(
                        f"  {query_name:30} {query_data['baseline']:>8.2f} → {query_data['current']:>8.2f} {query_data['formatted_change']}"
                    )
            elif isinstance(data, dict) and "baseline" in data:
                baseline_val = data["baseline"]
                current_val = data["current"]
                change = data["formatted_change"]
                print(f"{metric_name:35} {baseline_val:>10.2f} → {current_val:>10.2f} {change}")

        # Display regressions
        if comparison["regressions"]:
            print("\n⚠️  Performance Regressions:")
            print("-" * 60)
            for reg in comparison["regressions"]:
                print(
                    f"  {reg['metric']}: {reg['baseline']:.2f} → {reg['current']:.2f} (+{reg['percent_change']:.1f}%)"
                )

        # Display improvements
        if comparison["improvements"]:
            print("\n✅ Performance Improvements:")
            print("-" * 60)
            for imp in comparison["improvements"]:
                print(
                    f"  {imp['metric']}: {imp['baseline']:.2f} → {imp['current']:.2f} ({imp['percent_change']:.1f}%)"
                )

    def save_comparison(self, comparison: dict[str, Any], output_file: str) -> None:
        """Save comparison results to file"""
        with open(output_file, "w") as f:
            json.dump(comparison, f, indent=2)
        print(f"\nComparison results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Compare current performance against baseline")
    parser.add_argument(
        "--baseline", type=str, required=True, help="Baseline tag to compare against"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=10.0,
        help="Threshold percentage for significant changes (default: 10.0)",
    )
    parser.add_argument("--output", type=str, help="Save comparison results to JSON file")
    parser.add_argument(
        "--baseline-file",
        type=str,
        default="performance_baselines.json",
        help="File containing baselines (default: performance_baselines.json)",
    )

    args = parser.parse_args()

    # Create comparison runner
    comparator = PerformanceComparison(args.baseline_file)

    # Get baseline
    baseline = comparator.get_baseline(args.baseline)
    if not baseline:
        print(f"Error: Baseline '{args.baseline}' not found")
        print("\nAvailable baselines:")
        for tag in comparator.baselines:
            print(f"  - {tag}")
        sys.exit(1)

    # Measure current performance
    current = comparator.measure_current_performance()

    # Compare
    comparison = comparator.compare_metrics(baseline, current, args.threshold)

    # Generate report
    comparator.generate_report(comparison)

    # Save if requested
    if args.output:
        comparator.save_comparison(comparison, args.output)

    # Exit with non-zero code if regressions detected
    if comparison["regressions"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
