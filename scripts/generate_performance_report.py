#!/usr/bin/env python3
"""
Generate comprehensive performance reports for FastIntercom MCP
Creates detailed reports with trends and visualizations
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class PerformanceReporter:
    """Generate performance reports from test results"""

    def __init__(self):
        self.test_results_dir = Path("test_results")
        self.performance_data = []

    def load_test_results(self, days: int = 7) -> list[dict[str, Any]]:
        """Load test results from the last N days"""
        if not self.test_results_dir.exists():
            print(f"No test results directory found at {self.test_results_dir}")
            return []

        cutoff_date = datetime.now() - timedelta(days=days)
        results = []

        # Load all JSON files from test results
        for file_path in self.test_results_dir.glob("*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)

                # Check if file has performance metrics
                if "performance_metrics" in data or "metrics" in data:
                    # Try to get timestamp
                    timestamp = None
                    if "timestamp" in data:
                        timestamp = datetime.fromisoformat(data["timestamp"])
                    elif "date" in data:
                        timestamp = datetime.fromisoformat(data["date"])
                    else:
                        # Use file modification time
                        timestamp = datetime.fromtimestamp(file_path.stat().st_mtime)

                    if timestamp >= cutoff_date:
                        data["_filename"] = file_path.name
                        data["_timestamp"] = timestamp.isoformat()
                        results.append(data)

            except Exception as e:
                print(f"Warning: Could not load {file_path}: {e}")

        # Sort by timestamp
        results.sort(key=lambda x: x.get("_timestamp", ""))

        return results

    def extract_metrics(self, test_data: dict[str, Any]) -> dict[str, Any]:
        """Extract key metrics from test data"""
        metrics = {}

        # Handle different data formats
        if "performance_metrics" in test_data:
            perf = test_data["performance_metrics"]
            metrics.update(
                {
                    "sync_speed": perf.get("sync_speed", perf.get("conversations_per_second")),
                    "sync_duration": perf.get("sync_duration", perf.get("duration_seconds")),
                    "conversations_synced": perf.get("conversations_synced"),
                    "messages_synced": perf.get("messages_synced"),
                    "memory_usage_mb": perf.get("memory_usage_mb"),
                    "response_time_ms": perf.get("avg_response_time_ms"),
                }
            )

        if "metrics" in test_data:
            m = test_data["metrics"]
            metrics.update(
                {
                    "import_time_seconds": m.get("import_time_seconds"),
                    "cli_startup_seconds": m.get("cli_startup_seconds"),
                    "database_size_mb": m.get("database_size_mb"),
                    "avg_query_time_ms": m.get("avg_query_time_ms"),
                }
            )

        # Remove None values
        return {k: v for k, v in metrics.items() if v is not None}

    def calculate_statistics(self, values: list[float]) -> dict[str, float]:
        """Calculate statistics for a list of values"""
        if not values:
            return {}

        values = sorted(values)
        n = len(values)

        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / n,
            "median": values[n // 2] if n % 2 else (values[n // 2 - 1] + values[n // 2]) / 2,
            "p95": values[int(n * 0.95)] if n > 1 else values[0],
            "std_dev": (sum((x - sum(values) / n) ** 2 for x in values) / n) ** 0.5 if n > 1 else 0,
        }

    def generate_trend_analysis(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze performance trends over time"""
        if not results:
            return {}

        # Group metrics by type
        metric_series = {}

        for result in results:
            metrics = self.extract_metrics(result)
            timestamp = result.get("_timestamp", "")

            for metric_name, value in metrics.items():
                if metric_name not in metric_series:
                    metric_series[metric_name] = []

                metric_series[metric_name].append({"timestamp": timestamp, "value": value})

        # Calculate trends
        trends = {}
        for metric_name, series in metric_series.items():
            if len(series) > 1:
                values = [point["value"] for point in series]

                # Simple linear regression for trend
                n = len(values)
                x = list(range(n))
                y = values

                x_mean = sum(x) / n
                y_mean = sum(y) / n

                numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
                denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

                if denominator != 0:
                    slope = numerator / denominator
                    trend_direction = (
                        "improving" if slope < 0 else "degrading" if slope > 0 else "stable"
                    )
                    trend_percent = abs(slope / y_mean * 100) if y_mean != 0 else 0
                else:
                    trend_direction = "stable"
                    trend_percent = 0

                trends[metric_name] = {
                    "direction": trend_direction,
                    "change_percent": trend_percent,
                    "data_points": len(series),
                    "statistics": self.calculate_statistics(values),
                }

        return trends

    def generate_markdown_report(self, results: list[dict[str, Any]], output_file: str) -> None:
        """Generate a markdown performance report"""
        if not results:
            print("No results to report")
            return

        # Analyze trends
        trends = self.generate_trend_analysis(results)

        # Start report
        report_lines = [
            "# FastIntercom MCP Performance Report",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\nAnalysis Period: Last {len(results)} test runs",
            "",
        ]

        # Executive Summary
        report_lines.extend(["## Executive Summary", ""])

        # Key metrics summary
        latest_result = results[-1] if results else {}
        latest_metrics = self.extract_metrics(latest_result)

        if latest_metrics:
            report_lines.append("### Latest Performance Metrics")
            report_lines.append("")
            report_lines.append("| Metric | Value |")
            report_lines.append("|--------|-------|")

            for metric, value in latest_metrics.items():
                formatted_value = f"{value:.2f}" if isinstance(value, float) else str(value)

                # Add units
                if "time" in metric or "duration" in metric:
                    formatted_value += "s"
                elif "_ms" in metric:
                    formatted_value += "ms"
                elif "_mb" in metric:
                    formatted_value += " MB"
                elif "speed" in metric:
                    formatted_value += " conv/s"

                report_lines.append(f"| {metric.replace('_', ' ').title()} | {formatted_value} |")

            report_lines.append("")

        # Performance Trends
        if trends:
            report_lines.extend(["## Performance Trends", ""])

            improving = [m for m, t in trends.items() if t["direction"] == "improving"]
            degrading = [m for m, t in trends.items() if t["direction"] == "degrading"]
            stable = [m for m, t in trends.items() if t["direction"] == "stable"]

            if improving:
                report_lines.extend(["### ✅ Improving Metrics", ""])
                for metric in improving:
                    trend = trends[metric]
                    report_lines.append(
                        f"- **{metric.replace('_', ' ').title()}**: {trend['change_percent']:.1f}% improvement"
                    )
                report_lines.append("")

            if degrading:
                report_lines.extend(["### ⚠️ Degrading Metrics", ""])
                for metric in degrading:
                    trend = trends[metric]
                    report_lines.append(
                        f"- **{metric.replace('_', ' ').title()}**: {trend['change_percent']:.1f}% degradation"
                    )
                report_lines.append("")

            if stable:
                report_lines.extend(["### 📊 Stable Metrics", ""])
                for metric in stable:
                    report_lines.append(f"- {metric.replace('_', ' ').title()}")
                report_lines.append("")

        # Detailed Statistics
        report_lines.extend(["## Detailed Statistics", ""])

        for metric_name, trend_data in trends.items():
            if "statistics" in trend_data:
                stats = trend_data["statistics"]
                report_lines.extend(
                    [
                        f"### {metric_name.replace('_', ' ').title()}",
                        "",
                        f"- **Data Points**: {trend_data['data_points']}",
                        f"- **Min**: {stats['min']:.2f}",
                        f"- **Max**: {stats['max']:.2f}",
                        f"- **Average**: {stats['avg']:.2f}",
                        f"- **Median**: {stats['median']:.2f}",
                        f"- **95th Percentile**: {stats['p95']:.2f}",
                        f"- **Std Deviation**: {stats['std_dev']:.2f}",
                        "",
                    ]
                )

        # Performance Targets
        report_lines.extend(
            [
                "## Performance Targets",
                "",
                "| Metric | Target | Current | Status |",
                "|--------|--------|---------|--------|",
            ]
        )

        # Define targets
        targets = {
            "sync_speed": (10, "conv/s", "higher"),
            "response_time_ms": (100, "ms", "lower"),
            "memory_usage_mb": (100, "MB", "lower"),
            "cli_startup_seconds": (3, "s", "lower"),
            "import_time_seconds": (1, "s", "lower"),
        }

        for metric, (target, unit, direction) in targets.items():
            if metric in latest_metrics:
                current = latest_metrics[metric]
                if direction == "higher":
                    status = "✅ Pass" if current >= target else "❌ Fail"
                else:
                    status = "✅ Pass" if current <= target else "❌ Fail"

                report_lines.append(
                    f"| {metric.replace('_', ' ').title()} | {target} {unit} | {current:.2f} {unit} | {status} |"
                )

        report_lines.extend(["", ""])

        # Recommendations
        report_lines.extend(["## Recommendations", ""])

        # Generate recommendations based on data
        recommendations = []

        for metric in degrading:
            if "memory" in metric:
                recommendations.append("- Investigate memory usage patterns and potential leaks")
            elif "sync" in metric:
                recommendations.append(
                    "- Review sync algorithm efficiency and API call optimization"
                )
            elif "query" in metric:
                recommendations.append("- Analyze database query patterns and index usage")

        if not recommendations:
            recommendations.append("- Continue monitoring performance metrics")
            recommendations.append("- Consider establishing stricter performance budgets")

        report_lines.extend(recommendations)
        report_lines.append("")

        # Write report
        with open(output_file, "w") as f:
            f.write("\n".join(report_lines))

        print(f"Performance report generated: {output_file}")

    def generate_json_report(self, results: list[dict[str, Any]], output_file: str) -> None:
        """Generate a JSON performance report"""
        trends = self.generate_trend_analysis(results)

        report = {
            "generated_at": datetime.now().isoformat(),
            "analysis_period_days": len(results),
            "total_test_runs": len(results),
            "latest_metrics": self.extract_metrics(results[-1]) if results else {},
            "trends": trends,
            "raw_results": results,
        }

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"JSON report generated: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate performance report for FastIntercom MCP")
    parser.add_argument(
        "--last-days", type=int, default=7, help="Analyze results from the last N days (default: 7)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="performance_report.md",
        help="Output file for the report (default: performance_report.md)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json", "both"],
        default="markdown",
        help="Report format (default: markdown)",
    )
    parser.add_argument(
        "--test-results-dir",
        type=str,
        default="test_results",
        help="Directory containing test results (default: test_results)",
    )

    args = parser.parse_args()

    # Create reporter
    reporter = PerformanceReporter()
    if args.test_results_dir:
        reporter.test_results_dir = Path(args.test_results_dir)

    # Load results
    results = reporter.load_test_results(args.last_days)

    if not results:
        print(f"No test results found in the last {args.last_days} days")
        sys.exit(1)

    print(f"Found {len(results)} test results from the last {args.last_days} days")

    # Generate reports
    if args.format in ["markdown", "both"]:
        output_file = args.output if args.output.endswith(".md") else args.output + ".md"
        reporter.generate_markdown_report(results, output_file)

    if args.format in ["json", "both"]:
        output_file = (
            args.output.replace(".md", ".json")
            if args.output.endswith(".md")
            else args.output + ".json"
        )
        reporter.generate_json_report(results, output_file)


if __name__ == "__main__":
    main()
