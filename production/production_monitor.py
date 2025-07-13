#!/usr/bin/env python3
"""
Manufacturing Production Monitor for Sunflower AI
Real-time monitoring and tracking of USB production batches.

This tool provides a dashboard view of manufacturing progress,
quality control status, and production metrics.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import csv
from typing import Dict, List, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Note: Install 'rich' for better display: pip install rich")


class ProductionMonitor:
    def __init__(self, manufacturing_dir=None):
        self.manufacturing_dir = Path(manufacturing_dir or "manufacturing")
        self.console = Console() if RICH_AVAILABLE else None
        
        # Data storage
        self.batches = {}
        self.validation_results = defaultdict(list)
        self.production_stats = {
            "total_units_planned": 0,
            "total_units_validated": 0,
            "total_units_passed": 0,
            "total_units_failed": 0,
            "batches_active": 0,
            "batches_completed": 0
        }
        
        # Paths
        self.batch_records_dir = self.manufacturing_dir / "batch_records"
        self.validation_reports_dir = Path("validation_reports")
    
    def scan_batches(self):
        """Scan for all batch records"""
        self.batches.clear()
        
        if not self.batch_records_dir.exists():
            return
        
        # Scan batch record files
        for batch_file in self.batch_records_dir.glob("batch_*.json"):
            try:
                with open(batch_file) as f:
                    batch_data = json.load(f)
                
                batch_id = batch_data.get("batch_id", "unknown")
                self.batches[batch_id] = {
                    "file": batch_file,
                    "data": batch_data,
                    "status": self.determine_batch_status(batch_data),
                    "progress": self.calculate_batch_progress(batch_id, batch_data)
                }
            except Exception as e:
                if self.console:
                    self.console.print(f"[red]Error reading {batch_file}: {e}[/red]")
    
    def scan_validations(self):
        """Scan validation reports"""
        self.validation_results.clear()
        
        if not self.validation_reports_dir.exists():
            return
        
        # Read summary CSV if exists
        summary_file = self.validation_reports_dir / "validation_summary.csv"
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    batch_id = row.get("Batch", "unknown")
                    self.validation_results[batch_id].append(row)
    
    def determine_batch_status(self, batch_data):
        """Determine batch production status"""
        if "completed" in batch_data:
            return "completed"
        elif "iso" in batch_data.get("components", {}):
            return "in_production"
        else:
            return "preparing"
    
    def calculate_batch_progress(self, batch_id, batch_data):
        """Calculate batch production progress"""
        batch_size = batch_data.get("size", 100)
        
        # Count validated units for this batch
        validated = len(self.validation_results.get(batch_id, []))
        passed = sum(1 for v in self.validation_results.get(batch_id, []) 
                    if v.get("Status") == "PASS")
        failed = sum(1 for v in self.validation_results.get(batch_id, [])
                    if v.get("Status") == "FAIL")
        
        return {
            "total": batch_size,
            "validated": validated,
            "passed": passed,
            "failed": failed,
            "remaining": batch_size - validated,
            "percentage": (validated / batch_size * 100) if batch_size > 0 else 0
        }
    
    def update_stats(self):
        """Update overall production statistics"""
        self.production_stats["batches_active"] = sum(
            1 for b in self.batches.values() 
            if b["status"] == "in_production"
        )
        self.production_stats["batches_completed"] = sum(
            1 for b in self.batches.values()
            if b["status"] == "completed"
        )
        
        total_planned = 0
        total_validated = 0
        total_passed = 0
        total_failed = 0
        
        for batch_id, batch_info in self.batches.items():
            progress = batch_info["progress"]
            total_planned += progress["total"]
            total_validated += progress["validated"]
            total_passed += progress["passed"]
            total_failed += progress["failed"]
        
        self.production_stats.update({
            "total_units_planned": total_planned,
            "total_units_validated": total_validated,
            "total_units_passed": total_passed,
            "total_units_failed": total_failed
        })
    
    def display_dashboard(self):
        """Display production dashboard"""
        if not RICH_AVAILABLE:
            self.display_simple()
            return
        
        # Create layout
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="stats", ratio=1),
            Layout(name="batches", ratio=2)
        )
        
        # Header
        header = Panel(
            f"[bold cyan]Sunflower AI Production Monitor[/bold cyan]\n"
            f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            box=box.DOUBLE
        )
        layout["header"].update(header)
        
        # Statistics panel
        stats_table = Table(title="Production Statistics", box=box.ROUNDED)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", justify="right")
        
        stats_table.add_row("Active Batches", str(self.production_stats["batches_active"]))
        stats_table.add_row("Completed Batches", str(self.production_stats["batches_completed"]))
        stats_table.add_row("Total Units Planned", str(self.production_stats["total_units_planned"]))
        stats_table.add_row("Units Validated", str(self.production_stats["total_units_validated"]))
        stats_table.add_row("Units Passed", f"[green]{self.production_stats['total_units_passed']}[/green]")
        stats_table.add_row("Units Failed", f"[red]{self.production_stats['total_units_failed']}[/red]")
        
        if self.production_stats["total_units_validated"] > 0:
            pass_rate = (self.production_stats["total_units_passed"] / 
                        self.production_stats["total_units_validated"] * 100)
            stats_table.add_row("Pass Rate", f"{pass_rate:.1f}%")
        
        layout["stats"].update(Panel(stats_table))
        
        # Batches panel
        batch_table = Table(title="Batch Status", box=box.ROUNDED)
        batch_table.add_column("Batch ID", style="cyan")
        batch_table.add_column("Status")
        batch_table.add_column("Progress", justify="right")
        batch_table.add_column("Passed", justify="right", style="green")
        batch_table.add_column("Failed", justify="right", style="red")
        batch_table.add_column("Remaining", justify="right")
        
        for batch_id, batch_info in sorted(self.batches.items()):
            progress = batch_info["progress"]
            status = batch_info["status"]
            
            # Status with color
            if status == "completed":
                status_display = "[green]Completed[/green]"
            elif status == "in_production":
                status_display = "[yellow]In Production[/yellow]"
            else:
                status_display = "[blue]Preparing[/blue]"
            
            # Progress bar
            progress_str = f"{progress['percentage']:.0f}% ({progress['validated']}/{progress['total']})"
            
            batch_table.add_row(
                batch_id,
                status_display,
                progress_str,
                str(progress["passed"]),
                str(progress["failed"]),
                str(progress["remaining"])
            )
        
        layout["batches"].update(Panel(batch_table))
        
        # Footer
        footer = Panel(
            "[dim]Press Ctrl+C to exit | Auto-refreshes every 5 seconds[/dim]",
            box=box.SINGLE
        )
        layout["footer"].update(footer)
        
        self.console.print(layout)
    
    def display_simple(self):
        """Simple text display for environments without rich"""
        print("\n" + "=" * 80)
        print("SUNFLOWER AI PRODUCTION MONITOR")
        print(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        print("\nProduction Statistics:")
        print(f"  Active Batches: {self.production_stats['batches_active']}")
        print(f"  Completed Batches: {self.production_stats['batches_completed']}")
        print(f"  Total Units Planned: {self.production_stats['total_units_planned']}")
        print(f"  Units Validated: {self.production_stats['total_units_validated']}")
        print(f"  Units Passed: {self.production_stats['total_units_passed']}")
        print(f"  Units Failed: {self.production_stats['total_units_failed']}")
        
        if self.production_stats["total_units_validated"] > 0:
            pass_rate = (self.production_stats["total_units_passed"] / 
                        self.production_stats["total_units_validated"] * 100)
            print(f"  Pass Rate: {pass_rate:.1f}%")
        
        print("\nBatch Status:")
        print(f"{'Batch ID':<20} {'Status':<15} {'Progress':<20} {'Passed':<10} {'Failed':<10}")
        print("-" * 80)
        
        for batch_id, batch_info in sorted(self.batches.items()):
            progress = batch_info["progress"]
            progress_str = f"{progress['percentage']:.0f}% ({progress['validated']}/{progress['total']})"
            
            print(f"{batch_id:<20} {batch_info['status']:<15} {progress_str:<20} "
                  f"{progress['passed']:<10} {progress['failed']:<10}")
    
    def generate_report(self, output_file=None):
        """Generate detailed production report"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"production_report_{timestamp}.json"
        
        report = {
            "generated": datetime.now().isoformat(),
            "statistics": self.production_stats,
            "batches": {}
        }
        
        for batch_id, batch_info in self.batches.items():
            report["batches"][batch_id] = {
                "status": batch_info["status"],
                "progress": batch_info["progress"],
                "created": batch_info["data"].get("created"),
                "version": batch_info["data"].get("version"),
                "validation_details": self.validation_results.get(batch_id, [])
            }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        if self.console:
            self.console.print(f"\n[green]Report saved: {output_file}[/green]")
        else:
            print(f"\nReport saved: {output_file}")
        
        return output_file
    
    def monitor_loop(self, refresh_interval=5):
        """Main monitoring loop"""
        try:
            while True:
                # Scan for updates
                self.scan_batches()
                self.scan_validations()
                self.update_stats()
                
                # Clear screen
                os.system('cls' if os.name == 'nt' else 'clear')
                
                # Display dashboard
                self.display_dashboard()
                
                # Wait
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            if self.console:
                self.console.print("\n[yellow]Monitoring stopped by user[/yellow]")
            else:
                print("\nMonitoring stopped by user")
    
    def find_issues(self):
        """Identify production issues that need attention"""
        issues = []
        
        # Check for high failure rates
        for batch_id, batch_info in self.batches.items():
            progress = batch_info["progress"]
            if progress["failed"] > 0:
                fail_rate = progress["failed"] / max(progress["validated"], 1) * 100
                if fail_rate > 5:  # More than 5% failure
                    issues.append({
                        "batch": batch_id,
                        "type": "high_failure_rate",
                        "severity": "high",
                        "message": f"Failure rate {fail_rate:.1f}% exceeds threshold"
                    })
        
        # Check for stalled batches
        for batch_id, batch_info in self.batches.items():
            if batch_info["status"] == "in_production":
                created = datetime.fromisoformat(batch_info["data"].get("created", ""))
                age_days = (datetime.now() - created).days
                
                if age_days > 7:  # Batch older than 7 days
                    issues.append({
                        "batch": batch_id,
                        "type": "stalled_batch",
                        "severity": "medium",
                        "message": f"Batch in production for {age_days} days"
                    })
        
        return issues
    
    def alert_issues(self):
        """Display any production issues"""
        issues = self.find_issues()
        
        if not issues:
            return
        
        if self.console:
            self.console.print("\n[bold red]⚠️ Production Issues Detected:[/bold red]")
            for issue in issues:
                severity_color = "red" if issue["severity"] == "high" else "yellow"
                self.console.print(
                    f"  [{severity_color}]• {issue['batch']}: {issue['message']}[/{severity_color}]"
                )
        else:
            print("\n⚠️ Production Issues Detected:")
            for issue in issues:
                print(f"  • {issue['batch']}: {issue['message']} ({issue['severity']})")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor Sunflower AI USB production"
    )
    parser.add_argument(
        "--dir",
        default="manufacturing",
        help="Manufacturing directory path"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (no loop)"
    )
    parser.add_argument(
        "--report",
        help="Generate report and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Refresh interval in seconds (default: 5)"
    )
    
    args = parser.parse_args()
    
    monitor = ProductionMonitor(manufacturing_dir=args.dir)
    
    # Scan data
    monitor.scan_batches()
    monitor.scan_validations()
    monitor.update_stats()
    
    if args.report:
        # Generate report mode
        monitor.generate_report(args.report)
    elif args.once:
        # Display once mode
        monitor.display_dashboard()
        monitor.alert_issues()
    else:
        # Continuous monitoring mode
        monitor.monitor_loop(refresh_interval=args.interval)


if __name__ == "__main__":
    main()