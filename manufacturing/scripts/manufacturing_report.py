#!/usr/bin/env python3
"""
Sunflower AI Professional System - Manufacturing Report Generator
Generates comprehensive production reports and analytics
Version: 1.0.0
Author: Sunflower AI Production Team
"""

import os
import sys
import json
import csv
import time
import logging
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import argparse
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('manufacturing_reports.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProductionAnalyzer:
    """Analyzes production data and generates insights"""
    
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.build_reports = []
        self.validation_reports = []
        self.production_stats = {}
        
    def load_reports(self, start_date: Optional[datetime] = None, 
                    end_date: Optional[datetime] = None) -> bool:
        """Load production reports within date range"""
        try:
            # Load build reports
            build_dir = self.reports_dir / 'manufacturing_reports'
            if build_dir.exists():
                for report_file in build_dir.glob('build_*.json'):
                    try:
                        with open(report_file, 'r') as f:
                            report = json.load(f)
                            
                        # Parse date
                        report_date = datetime.fromisoformat(report.get('build_date', ''))
                        
                        # Check date range
                        if start_date and report_date < start_date:
                            continue
                        if end_date and report_date > end_date:
                            continue
                            
                        self.build_reports.append(report)
                        
                    except Exception as e:
                        logger.warning(f"Failed to load build report {report_file}: {e}")
                        
            # Load validation reports
            validation_dir = self.reports_dir / 'validation_reports'
            if validation_dir.exists():
                for report_file in validation_dir.glob('validation_*.json'):
                    try:
                        with open(report_file, 'r') as f:
                            report = json.load(f)
                            
                        # Parse date
                        report_date = datetime.fromisoformat(report.get('validation_date', ''))
                        
                        # Check date range
                        if start_date and report_date < start_date:
                            continue
                        if end_date and report_date > end_date:
                            continue
                            
                        self.validation_reports.append(report)
                        
                    except Exception as e:
                        logger.warning(f"Failed to load validation report {report_file}: {e}")
                        
            logger.info(f"Loaded {len(self.build_reports)} build reports and "
                       f"{len(self.validation_reports)} validation reports")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load reports: {e}")
            return False
            
    def calculate_statistics(self):
        """Calculate production statistics"""
        try:
            # Build statistics
            if self.build_reports:
                build_times = [r.get('build_time', 0) for r in self.build_reports]
                
                self.production_stats['build'] = {
                    'total_builds': len(self.build_reports),
                    'successful_builds': sum(1 for r in self.build_reports 
                                           if r.get('status') == 'SUCCESS'),
                    'failed_builds': sum(1 for r in self.build_reports 
                                       if r.get('status') != 'SUCCESS'),
                    'average_build_time': statistics.mean(build_times) if build_times else 0,
                    'median_build_time': statistics.median(build_times) if build_times else 0,
                    'min_build_time': min(build_times) if build_times else 0,
                    'max_build_time': max(build_times) if build_times else 0
                }
                
                # Platform distribution
                platforms = [r.get('platform', 'Unknown') for r in self.build_reports]
                self.production_stats['build']['platform_distribution'] = dict(Counter(platforms))
                
            # Validation statistics
            if self.validation_reports:
                validation_times = [r.get('validation_time', 0) for r in self.validation_reports]
                
                self.production_stats['validation'] = {
                    'total_validations': len(self.validation_reports),
                    'passed_validations': sum(1 for r in self.validation_reports 
                                            if r.get('overall_result') == 'PASS'),
                    'failed_validations': sum(1 for r in self.validation_reports 
                                            if r.get('overall_result') == 'FAIL'),
                    'average_validation_time': statistics.mean(validation_times) if validation_times else 0,
                    'pass_rate': (sum(1 for r in self.validation_reports 
                                    if r.get('overall_result') == 'PASS') / 
                                len(self.validation_reports) * 100) if self.validation_reports else 0
                }
                
                # Common failure reasons
                failures = []
                for report in self.validation_reports:
                    if report.get('overall_result') == 'FAIL':
                        for test in report.get('test_results', []):
                            if not test.get('passed'):
                                failures.append(test.get('name'))
                                
                self.production_stats['validation']['common_failures'] = dict(Counter(failures))
                
            # Quality metrics
            if self.build_reports and self.validation_reports:
                # Match builds to validations by device UUID
                validated_builds = set()
                for val_report in self.validation_reports:
                    device_uuid = val_report.get('device_uuid')
                    if device_uuid and val_report.get('overall_result') == 'PASS':
                        validated_builds.add(device_uuid)
                        
                build_uuids = set(r.get('build_id') for r in self.build_reports)
                
                self.production_stats['quality'] = {
                    'first_pass_yield': (len(validated_builds) / len(build_uuids) * 100) 
                                       if build_uuids else 0,
                    'validated_devices': len(validated_builds),
                    'total_manufactured': len(build_uuids)
                }
                
        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
            
    def identify_trends(self) -> Dict:
        """Identify production trends and patterns"""
        trends = {
            'daily_production': {},
            'failure_trends': {},
            'performance_trends': {}
        }
        
        try:
            # Daily production trends
            daily_builds = defaultdict(int)
            daily_validations = defaultdict(int)
            
            for report in self.build_reports:
                date = datetime.fromisoformat(report.get('build_date', '')).date()
                daily_builds[date.isoformat()] += 1
                
            for report in self.validation_reports:
                date = datetime.fromisoformat(report.get('validation_date', '')).date()
                daily_validations[date.isoformat()] += 1
                
            trends['daily_production'] = {
                'builds': dict(daily_builds),
                'validations': dict(daily_validations)
            }
            
            # Failure trends over time
            daily_failures = defaultdict(lambda: {'total': 0, 'failures': 0})
            
            for report in self.validation_reports:
                date = datetime.fromisoformat(report.get('validation_date', '')).date()
                daily_failures[date.isoformat()]['total'] += 1
                if report.get('overall_result') == 'FAIL':
                    daily_failures[date.isoformat()]['failures'] += 1
                    
            trends['failure_trends'] = dict(daily_failures)
            
            # Performance trends (build times)
            if self.build_reports:
                sorted_builds = sorted(self.build_reports, 
                                     key=lambda x: x.get('build_date', ''))
                
                # Calculate moving average
                window_size = 10
                if len(sorted_builds) >= window_size:
                    moving_avg = []
                    for i in range(window_size, len(sorted_builds) + 1):
                        window = sorted_builds[i-window_size:i]
                        avg_time = statistics.mean([r.get('build_time', 0) for r in window])
                        moving_avg.append({
                            'date': window[-1].get('build_date'),
                            'average_build_time': avg_time
                        })
                    trends['performance_trends']['build_time_trend'] = moving_avg
                    
        except Exception as e:
            logger.error(f"Failed to identify trends: {e}")
            
        return trends
        
    def generate_quality_report(self) -> Dict:
        """Generate quality control report"""
        quality_report = {
            'summary': {},
            'test_performance': {},
            'device_tracking': {},
            'recommendations': []
        }
        
        try:
            # Summary metrics
            total_devices = len(self.build_reports)
            passed_devices = sum(1 for r in self.validation_reports 
                               if r.get('overall_result') == 'PASS')
            
            quality_report['summary'] = {
                'total_manufactured': total_devices,
                'validated_passed': passed_devices,
                'yield_rate': (passed_devices / total_devices * 100) if total_devices else 0,
                'rejection_rate': ((total_devices - passed_devices) / total_devices * 100) 
                                if total_devices else 0
            }
            
            # Test performance analysis
            test_stats = defaultdict(lambda: {'total': 0, 'passed': 0})
            
            for report in self.validation_reports:
                for test in report.get('test_results', []):
                    test_name = test.get('name')
                    test_stats[test_name]['total'] += 1
                    if test.get('passed'):
                        test_stats[test_name]['passed'] += 1
                        
            for test_name, stats in test_stats.items():
                quality_report['test_performance'][test_name] = {
                    'pass_rate': (stats['passed'] / stats['total'] * 100) 
                               if stats['total'] else 0,
                    'total_runs': stats['total'],
                    'passed': stats['passed'],
                    'failed': stats['total'] - stats['passed']
                }
                
            # Device tracking
            device_status = {}
            for report in self.build_reports:
                device_uuid = report.get('build_id')
                device_status[device_uuid] = {
                    'build_date': report.get('build_date'),
                    'build_status': report.get('status'),
                    'validation_status': 'Not Validated'
                }
                
            for report in self.validation_reports:
                device_uuid = report.get('device_uuid')
                if device_uuid in device_status:
                    device_status[device_uuid]['validation_status'] = report.get('overall_result')
                    
            quality_report['device_tracking'] = device_status
            
            # Generate recommendations
            if quality_report['summary']['yield_rate'] < 90:
                quality_report['recommendations'].append(
                    f"Yield rate is {quality_report['summary']['yield_rate']:.1f}%. "
                    "Review manufacturing process for improvements."
                )
                
            # Check for consistent test failures
            for test_name, perf in quality_report['test_performance'].items():
                if perf['pass_rate'] < 95:
                    quality_report['recommendations'].append(
                        f"Test '{test_name}' has low pass rate ({perf['pass_rate']:.1f}%). "
                        "Investigate root cause."
                    )
                    
        except Exception as e:
            logger.error(f"Failed to generate quality report: {e}")
            
        return quality_report


class ReportGenerator:
    """Generates various manufacturing reports"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        
    def generate_daily_report(self, analyzer: ProductionAnalyzer, date: datetime) -> Path:
        """Generate daily production report"""
        try:
            report = {
                'report_type': 'Daily Production Report',
                'date': date.date().isoformat(),
                'generated': datetime.now().isoformat(),
                'statistics': analyzer.production_stats,
                'quality_metrics': {},
                'devices_manufactured': [],
                'devices_validated': []
            }
            
            # Filter reports for specific date
            date_str = date.date().isoformat()
            
            for build_report in analyzer.build_reports:
                build_date = datetime.fromisoformat(build_report.get('build_date', '')).date()
                if build_date.isoformat() == date_str:
                    report['devices_manufactured'].append({
                        'device_uuid': build_report.get('build_id'),
                        'build_time': build_report.get('build_time'),
                        'status': build_report.get('status'),
                        'platform': build_report.get('platform')
                    })
                    
            for val_report in analyzer.validation_reports:
                val_date = datetime.fromisoformat(val_report.get('validation_date', '')).date()
                if val_date.isoformat() == date_str:
                    report['devices_validated'].append({
                        'device_uuid': val_report.get('device_uuid'),
                        'validation_time': val_report.get('validation_time'),
                        'result': val_report.get('overall_result'),
                        'tests_passed': val_report.get('summary', {}).get('passed_tests', 0),
                        'tests_total': val_report.get('summary', {}).get('total_tests', 0)
                    })
                    
            # Calculate daily metrics
            report['quality_metrics'] = {
                'devices_built': len(report['devices_manufactured']),
                'devices_validated': len(report['devices_validated']),
                'validation_pass_rate': (
                    sum(1 for d in report['devices_validated'] if d['result'] == 'PASS') /
                    len(report['devices_validated']) * 100
                ) if report['devices_validated'] else 0
            }
            
            # Save report
            report_file = self.output_dir / f"daily_report_{date_str}.json"
            report_file.write_text(json.dumps(report, indent=2))
            
            logger.info(f"Daily report generated: {report_file}")
            return report_file
            
        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")
            return None
            
    def generate_batch_report(self, analyzer: ProductionAnalyzer, 
                            batch_id: str, device_uuids: List[str]) -> Path:
        """Generate batch production report"""
        try:
            report = {
                'report_type': 'Batch Production Report',
                'batch_id': batch_id,
                'generated': datetime.now().isoformat(),
                'device_count': len(device_uuids),
                'devices': [],
                'batch_statistics': {},
                'quality_summary': {}
            }
            
            # Collect device information
            for device_uuid in device_uuids:
                device_info = {'uuid': device_uuid}
                
                # Find build report
                for build_report in analyzer.build_reports:
                    if build_report.get('build_id') == device_uuid:
                        device_info['build'] = {
                            'date': build_report.get('build_date'),
                            'time': build_report.get('build_time'),
                            'status': build_report.get('status'),
                            'serial': build_report.get('metadata', {}).get('serial')
                        }
                        break
                        
                # Find validation report
                for val_report in analyzer.validation_reports:
                    if val_report.get('device_uuid') == device_uuid:
                        device_info['validation'] = {
                            'date': val_report.get('validation_date'),
                            'result': val_report.get('overall_result'),
                            'tests': val_report.get('summary')
                        }
                        break
                        
                report['devices'].append(device_info)
                
            # Calculate batch statistics
            build_times = []
            validation_results = []
            
            for device in report['devices']:
                if 'build' in device and device['build'].get('time'):
                    build_times.append(device['build']['time'])
                if 'validation' in device:
                    validation_results.append(device['validation'].get('result'))
                    
            report['batch_statistics'] = {
                'average_build_time': statistics.mean(build_times) if build_times else 0,
                'total_build_time': sum(build_times) if build_times else 0,
                'validated_count': len(validation_results),
                'passed_count': sum(1 for r in validation_results if r == 'PASS'),
                'failed_count': sum(1 for r in validation_results if r == 'FAIL')
            }
            
            report['quality_summary'] = {
                'batch_yield': (report['batch_statistics']['passed_count'] / 
                              len(device_uuids) * 100) if device_uuids else 0,
                'validation_coverage': (report['batch_statistics']['validated_count'] / 
                                       len(device_uuids) * 100) if device_uuids else 0
            }
            
            # Save report
            report_file = self.output_dir / f"batch_report_{batch_id}.json"
            report_file.write_text(json.dumps(report, indent=2))
            
            logger.info(f"Batch report generated: {report_file}")
            return report_file
            
        except Exception as e:
            logger.error(f"Failed to generate batch report: {e}")
            return None
            
    def generate_executive_summary(self, analyzer: ProductionAnalyzer, 
                                  period: str = "monthly") -> Path:
        """Generate executive summary report"""
        try:
            # Calculate period dates
            end_date = datetime.now()
            if period == "daily":
                start_date = end_date - timedelta(days=1)
            elif period == "weekly":
                start_date = end_date - timedelta(weeks=1)
            elif period == "monthly":
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(days=90)  # quarterly
                
            report = {
                'report_type': 'Executive Summary',
                'period': period,
                'start_date': start_date.date().isoformat(),
                'end_date': end_date.date().isoformat(),
                'generated': datetime.now().isoformat(),
                'key_metrics': {},
                'production_summary': analyzer.production_stats,
                'quality_report': analyzer.generate_quality_report(),
                'trends': analyzer.identify_trends(),
                'recommendations': []
            }
            
            # Calculate key metrics
            total_manufactured = analyzer.production_stats.get('build', {}).get('total_builds', 0)
            total_validated = analyzer.production_stats.get('validation', {}).get('total_validations', 0)
            passed_validation = analyzer.production_stats.get('validation', {}).get('passed_validations', 0)
            
            report['key_metrics'] = {
                'total_units_produced': total_manufactured,
                'total_units_validated': total_validated,
                'first_pass_yield': (passed_validation / total_manufactured * 100) 
                                   if total_manufactured else 0,
                'average_build_time_minutes': analyzer.production_stats.get('build', {}).get(
                    'average_build_time', 0) / 60,
                'validation_pass_rate': analyzer.production_stats.get('validation', {}).get(
                    'pass_rate', 0)
            }
            
            # Generate recommendations
            if report['key_metrics']['first_pass_yield'] < 95:
                report['recommendations'].append({
                    'priority': 'HIGH',
                    'area': 'Quality',
                    'recommendation': f"First pass yield is {report['key_metrics']['first_pass_yield']:.1f}%. "
                                    "Implement additional quality controls in manufacturing process."
                })
                
            if report['key_metrics']['average_build_time_minutes'] > 10:
                report['recommendations'].append({
                    'priority': 'MEDIUM',
                    'area': 'Efficiency',
                    'recommendation': f"Average build time is {report['key_metrics']['average_build_time_minutes']:.1f} minutes. "
                                    "Consider process optimization to reduce build time."
                })
                
            # Check for validation coverage
            validation_coverage = (total_validated / total_manufactured * 100) if total_manufactured else 0
            if validation_coverage < 100:
                report['recommendations'].append({
                    'priority': 'HIGH',
                    'area': 'Quality Control',
                    'recommendation': f"Only {validation_coverage:.1f}% of manufactured devices validated. "
                                    "Ensure all devices undergo validation before shipment."
                })
                
            # Save report
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = self.output_dir / f"executive_summary_{period}_{timestamp}.json"
            report_file.write_text(json.dumps(report, indent=2))
            
            # Also generate HTML version for executives
            self._generate_html_summary(report, report_file.with_suffix('.html'))
            
            logger.info(f"Executive summary generated: {report_file}")
            return report_file
            
        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}")
            return None
            
    def _generate_html_summary(self, report: Dict, output_file: Path):
        """Generate HTML version of executive summary"""
        try:
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sunflower AI Manufacturing Report - {report['period'].title()}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .metric-label {{
            color: #666;
            margin-top: 5px;
        }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .recommendation {{
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #ff6b6b;
            background: #fff5f5;
            border-radius: 5px;
        }}
        .recommendation.high {{
            border-left-color: #ff6b6b;
            background: #fff5f5;
        }}
        .recommendation.medium {{
            border-left-color: #ffd93d;
            background: #fffbf0;
        }}
        .recommendation.low {{
            border-left-color: #6bcf7f;
            background: #f0fdf4;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Manufacturing Report - {report['period'].title()}</h1>
        <p>Period: {report['start_date']} to {report['end_date']}</p>
        <p>Generated: {report['generated']}</p>
    </div>
    
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-value">{report['key_metrics']['total_units_produced']}</div>
            <div class="metric-label">Units Produced</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{report['key_metrics']['first_pass_yield']:.1f}%</div>
            <div class="metric-label">First Pass Yield</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{report['key_metrics']['validation_pass_rate']:.1f}%</div>
            <div class="metric-label">Validation Pass Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{report['key_metrics']['average_build_time_minutes']:.1f} min</div>
            <div class="metric-label">Avg Build Time</div>
        </div>
    </div>
    
    <div class="section">
        <h2>Production Summary</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Build Process</th>
                <th>Validation Process</th>
            </tr>
            <tr>
                <td>Total Count</td>
                <td>{report['production_summary'].get('build', {}).get('total_builds', 0)}</td>
                <td>{report['production_summary'].get('validation', {}).get('total_validations', 0)}</td>
            </tr>
            <tr>
                <td>Success Rate</td>
                <td>{(report['production_summary'].get('build', {}).get('successful_builds', 0) / 
                     report['production_summary'].get('build', {}).get('total_builds', 1) * 100):.1f}%</td>
                <td>{report['production_summary'].get('validation', {}).get('pass_rate', 0):.1f}%</td>
            </tr>
        </table>
    </div>
    
    <div class="section">
        <h2>Recommendations</h2>
        {"".join([f'''
        <div class="recommendation {rec.get('priority', 'medium').lower()}">
            <strong>{rec.get('area')}:</strong> {rec.get('recommendation')}
        </div>
        ''' for rec in report.get('recommendations', [])])}
    </div>
    
    <div class="section">
        <h2>Quality Metrics</h2>
        <p>Detailed quality control results and device tracking are available in the full JSON report.</p>
    </div>
</body>
</html>
"""
            
            output_file.write_text(html_content)
            logger.info(f"HTML summary generated: {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate HTML summary: {e}")
            
    def export_to_csv(self, analyzer: ProductionAnalyzer) -> Path:
        """Export production data to CSV for external analysis"""
        try:
            # Create CSV for build reports
            build_csv = self.output_dir / f"build_data_{datetime.now().strftime('%Y%m%d')}.csv"
            
            with open(build_csv, 'w', newline='') as f:
                if analyzer.build_reports:
                    fieldnames = ['device_uuid', 'build_date', 'build_time', 'status', 
                                'platform', 'serial_number']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for report in analyzer.build_reports:
                        writer.writerow({
                            'device_uuid': report.get('build_id'),
                            'build_date': report.get('build_date'),
                            'build_time': report.get('build_time'),
                            'status': report.get('status'),
                            'platform': report.get('platform'),
                            'serial_number': report.get('metadata', {}).get('serial')
                        })
                        
            # Create CSV for validation reports
            validation_csv = self.output_dir / f"validation_data_{datetime.now().strftime('%Y%m%d')}.csv"
            
            with open(validation_csv, 'w', newline='') as f:
                if analyzer.validation_reports:
                    fieldnames = ['device_uuid', 'validation_date', 'validation_time', 
                                'result', 'tests_passed', 'tests_total', 'critical_failures']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for report in analyzer.validation_reports:
                        writer.writerow({
                            'device_uuid': report.get('device_uuid'),
                            'validation_date': report.get('validation_date'),
                            'validation_time': report.get('validation_time'),
                            'result': report.get('overall_result'),
                            'tests_passed': report.get('summary', {}).get('passed_tests'),
                            'tests_total': report.get('summary', {}).get('total_tests'),
                            'critical_failures': report.get('summary', {}).get('critical_failures')
                        })
                        
            logger.info(f"CSV exports created: {build_csv}, {validation_csv}")
            return build_csv
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return None


def main():
    """Main entry point for manufacturing reporting"""
    parser = argparse.ArgumentParser(description='Sunflower AI Manufacturing Report Generator')
    parser.add_argument('--type', choices=['daily', 'batch', 'executive', 'export'],
                       default='executive', help='Type of report to generate')
    parser.add_argument('--period', choices=['daily', 'weekly', 'monthly', 'quarterly'],
                       default='monthly', help='Period for executive summary')
    parser.add_argument('--date', type=str, help='Date for daily report (YYYY-MM-DD)')
    parser.add_argument('--batch-id', type=str, help='Batch ID for batch report')
    parser.add_argument('--devices', type=str, help='Comma-separated device UUIDs for batch report')
    parser.add_argument('--output-dir', type=Path, default=Path('production_reports'),
                       help='Output directory for reports')
    parser.add_argument('--data-dir', type=Path, default=Path('.'),
                       help='Directory containing production data')
    
    args = parser.parse_args()
    
    try:
        print("=" * 60)
        print("Sunflower AI Manufacturing Report Generator")
        print("=" * 60)
        
        # Initialize analyzer
        analyzer = ProductionAnalyzer(args.data_dir)
        
        # Load reports
        print("\nLoading production data...")
        if not analyzer.load_reports():
            print("Failed to load production reports")
            sys.exit(1)
            
        # Calculate statistics
        print("Calculating statistics...")
        analyzer.calculate_statistics()
        
        # Initialize report generator
        generator = ReportGenerator(args.output_dir)
        
        # Generate requested report
        if args.type == 'daily':
            if args.date:
                date = datetime.strptime(args.date, '%Y-%m-%d')
            else:
                date = datetime.now()
                
            print(f"\nGenerating daily report for {date.date()}...")
            report_file = generator.generate_daily_report(analyzer, date)
            
        elif args.type == 'batch':
            if not args.batch_id or not args.devices:
                print("Batch ID and device UUIDs required for batch report")
                sys.exit(1)
                
            device_uuids = args.devices.split(',')
            print(f"\nGenerating batch report for {args.batch_id}...")
            report_file = generator.generate_batch_report(analyzer, args.batch_id, device_uuids)
            
        elif args.type == 'executive':
            print(f"\nGenerating {args.period} executive summary...")
            report_file = generator.generate_executive_summary(analyzer, args.period)
            
        elif args.type == 'export':
            print("\nExporting production data to CSV...")
            report_file = generator.export_to_csv(analyzer)
            
        if report_file:
            print(f"\n✓ Report generated successfully: {report_file}")
            
            # Display summary statistics
            print("\nProduction Statistics:")
            print(f"  Total Builds: {analyzer.production_stats.get('build', {}).get('total_builds', 0)}")
            print(f"  Total Validations: {analyzer.production_stats.get('validation', {}).get('total_validations', 0)}")
            print(f"  Validation Pass Rate: {analyzer.production_stats.get('validation', {}).get('pass_rate', 0):.1f}%")
            
            quality = analyzer.production_stats.get('quality', {})
            if quality:
                print(f"  First Pass Yield: {quality.get('first_pass_yield', 0):.1f}%")
                
        else:
            print("\n✗ Report generation failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nReport generation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n✗ Report generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
