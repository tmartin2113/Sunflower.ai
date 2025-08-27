# Quality Control Procedures

## Overview

This document defines comprehensive quality control procedures for manufacturing Sunflower AI Professional USB devices, ensuring every unit meets our stringent safety and performance standards.

## QC Standards

### Quality Objectives

```
Critical Requirements (0% Defect Tolerance):
├── Safety features functional
├── Age filtering operational  
├── Parent controls working
└── Data encryption active

Performance Requirements (<1% Defect Rate):
├── Boot time <30 seconds
├── Response time <3 seconds
├── Model loading successful
└── Profile creation working

Cosmetic Requirements (<3% Defect Rate):
├── USB casing intact
├── Labels properly affixed
├── Packaging undamaged
└── Documentation included
```

## Testing Phases

### Phase 1: Component Testing

#### USB Device Validation

```python
class USBDeviceQualityCheck:
    """Pre-production USB device testing"""
    
    def __init__(self):
        self.min_read_speed = 100  # MB/s
        self.min_write_speed = 30  # MB/s
        self.capacity_tolerance = 0.95  # 95% of advertised
        
    def test_usb_device(self, device_path):
        """Complete USB device quality check"""
        
        results = {
            "device": device_path,
            "timestamp": datetime.now(),
            "tests": {}
        }
        
        # Test 1: Capacity verification
        results["tests"]["capacity"] = self.verify_capacity(device_path)
        
        # Test 2: Read speed
        results["tests"]["read_speed"] = self.test_read_speed(device_path)
        
        # Test 3: Write speed  
        results["tests"]["write_speed"] = self.test_write_speed(device_path)
        
        # Test 4: Reliability
        results["tests"]["reliability"] = self.test_reliability(device_path)
        
        # Test 5: Partitioning capability
        results["tests"]["partitioning"] = self.test_partitioning(device_path)
        
        return self.evaluate_results(results)
    
    def test_read_speed(self, device_path):
        """Test sequential read speed"""
        
        test_file = device_path / "speed_test.tmp"
        size_mb = 100
        
        # Write test file
        with open(test_file, 'wb') as f:
            f.write(os.urandom(size_mb * 1024 * 1024))
        
        # Time reading
        start = time.time()
        with open(test_file, 'rb') as f:
            data = f.read()
        elapsed = time.time() - start
        
        speed = size_mb / elapsed
        os.remove(test_file)
        
        return {
            "speed_mbps": speed,
            "pass": speed >= self.min_read_speed
        }
```

### Phase 2: Production Testing

#### Partition Creation Verification

```python
class PartitionQualityCheck:
    """Verify dual-partition creation"""
    
    def verify_partitions(self, device):
        """Check partition structure"""
        
        checks = {
            "cdrom_partition": False,
            "usb_partition": False,
            "cdrom_read_only": False,
            "usb_writable": False,
            "partition_sizes": False
        }
        
        # Check CD-ROM partition
        cdrom = self.find_cdrom_partition(device)
        if cdrom:
            checks["cdrom_partition"] = True
            checks["cdrom_read_only"] = self.verify_read_only(cdrom)
            
        # Check USB partition
        usb = self.find_usb_partition(device)
        if usb:
            checks["usb_partition"] = True
            checks["usb_writable"] = self.verify_writable(usb)
        
        # Verify sizes
        if cdrom and usb:
            cdrom_size = self.get_partition_size(cdrom)
            usb_size = self.get_partition_size(usb)
            
            # CD-ROM should be ~4GB, USB should be remaining
            checks["partition_sizes"] = (
                3.8 <= cdrom_size <= 4.2 and
                usb_size >= 3.8
            )
        
        return all(checks.values()), checks
```

#### Content Integrity Verification

```python
class ContentIntegrityCheck:
    """Verify all files written correctly"""
    
    def __init__(self):
        self.manifest = self.load_manifest()
        
    def verify_content(self, device_path):
        """Check all files against manifest"""
        
        results = {
            "missing_files": [],
            "corrupt_files": [],
            "extra_files": [],
            "total_files": len(self.manifest),
            "verified_files": 0
        }
        
        # Check each file in manifest
        for file_path, expected_hash in self.manifest.items():
            full_path = device_path / file_path
            
            if not full_path.exists():
                results["missing_files"].append(file_path)
            else:
                actual_hash = self.calculate_hash(full_path)
                if actual_hash != expected_hash:
                    results["corrupt_files"].append(file_path)
                else:
                    results["verified_files"] += 1
        
        # Check for extra files
        for file_path in self.scan_device(device_path):
            if file_path not in self.manifest:
                results["extra_files"].append(file_path)
        
        results["pass"] = (
            len(results["missing_files"]) == 0 and
            len(results["corrupt_files"]) == 0
        )
        
        return results
```

### Phase 3: Functional Testing

#### System Boot Test

```python
class FunctionalQualityCheck:
    """Test actual functionality"""
    
    def test_system_boot(self, device):
        """Test complete system startup"""
        
        test_results = {
            "launcher_starts": False,
            "ollama_loads": False,
            "models_available": False,
            "webui_accessible": False,
            "safety_active": False,
            "boot_time": None
        }
        
        start_time = time.time()
        
        try:
            # Test 1: Launcher execution
            launcher = self.run_launcher(device)
            test_results["launcher_starts"] = launcher.returncode == 0
            
            # Test 2: Ollama service
            if self.check_ollama_running():
                test_results["ollama_loads"] = True
                
                # Test 3: Models loaded
                models = self.list_ollama_models()
                test_results["models_available"] = (
                    "sunflower-kids" in models and
                    "sunflower-educator" in models
                )
            
            # Test 4: Web UI accessible
            test_results["webui_accessible"] = self.check_webui_responding()
            
            # Test 5: Safety features
            test_results["safety_active"] = self.test_safety_filter()
            
            test_results["boot_time"] = time.time() - start_time
            
        except Exception as e:
            test_results["error"] = str(e)
        
        return test_results
```

#### Safety System Verification

```python
class SafetyQualityCheck:
    """Critical safety system testing"""
    
    def __init__(self):
        self.test_queries = self.load_safety_test_suite()
        
    def test_safety_system(self, device):
        """Comprehensive safety testing"""
        
        results = {
            "total_tests": len(self.test_queries),
            "passed": 0,
            "failed": [],
            "response_times": []
        }
        
        for test in self.test_queries:
            query = test["input"]
            expected = test["expected_behavior"]
            age = test["age_group"]
            
            # Set profile age
            self.set_test_profile_age(age)
            
            # Send query
            start = time.time()
            response = self.send_query(query)
            elapsed = time.time() - start
            
            results["response_times"].append(elapsed)
            
            # Verify response
            if self.verify_safety_response(response, expected):
                results["passed"] += 1
            else:
                results["failed"].append({
                    "query": query,
                    "expected": expected,
                    "actual": response,
                    "age": age
                })
        
        results["pass_rate"] = results["passed"] / results["total_tests"]
        results["avg_response_time"] = sum(results["response_times"]) / len(results["response_times"])
        
        # Safety must be 100%
        results["qa_pass"] = results["pass_rate"] == 1.0
        
        return results
```

### Phase 4: Stress Testing

#### Load Testing

```python
class StressTestQuality:
    """Stress test for reliability"""
    
    def stress_test_device(self, device, duration_minutes=10):
        """Run stress tests"""
        
        results = {
            "duration": duration_minutes,
            "queries_sent": 0,
            "successful_responses": 0,
            "errors": [],
            "memory_usage": [],
            "response_times": []
        }
        
        end_time = time.time() + (duration_minutes * 60)
        
        while time.time() < end_time:
            # Send rapid queries
            for _ in range(10):
                try:
                    start = time.time()
                    response = self.send_random_query()
                    elapsed = time.time() - start
                    
                    results["queries_sent"] += 1
                    
                    if response:
                        results["successful_responses"] += 1
                        results["response_times"].append(elapsed)
                    
                except Exception as e:
                    results["errors"].append(str(e))
            
            # Monitor resources
            results["memory_usage"].append(self.get_memory_usage())
            
            # Brief pause
            time.sleep(1)
        
        # Calculate statistics
        results["success_rate"] = results["successful_responses"] / results["queries_sent"]
        results["avg_response_time"] = sum(results["response_times"]) / len(results["response_times"])
        results["max_memory"] = max(results["memory_usage"])
        
        # Pass criteria
        results["qa_pass"] = (
            results["success_rate"] >= 0.99 and
            results["avg_response_time"] < 3.0 and
            results["max_memory"] < 2048  # MB
        )
        
        return results
```

## Testing Equipment

### Required Hardware

```yaml
QC Testing Station Requirements:
  
  Computers:
    - Windows 11 PC (8GB RAM minimum)
    - macOS device (M1 or Intel)
    - Linux machine (for cross-platform)
  
  USB Testing:
    - USB 3.0 speed tester
    - USB protocol analyzer
    - Multiple USB ports (3.0/3.1/USB-C)
  
  Automation:
    - Scriptable USB hub
    - Automated test runner
    - Barcode scanner for tracking
  
  Monitoring:
    - Performance profiler
    - Memory analyzer
    - Network monitor (ensure offline)
```

### Software Tools

```python
# QC Testing Software Suite

class QCTestingSuite:
    """Complete QC testing automation"""
    
    def __init__(self):
        self.test_modules = [
            USBDeviceQualityCheck(),
            PartitionQualityCheck(),
            ContentIntegrityCheck(),
            FunctionalQualityCheck(),
            SafetyQualityCheck(),
            StressTestQuality()
        ]
        
    def run_full_qa(self, device):
        """Run complete QA suite"""
        
        report = {
            "device_serial": self.get_device_serial(device),
            "test_date": datetime.now(),
            "test_station": platform.node(),
            "results": {}
        }
        
        for module in self.test_modules:
            module_name = module.__class__.__name__
            print(f"Running {module_name}...")
            
            try:
                result = module.run_test(device)
                report["results"][module_name] = result
                
                if not result.get("qa_pass", False):
                    report["overall_result"] = "FAIL"
                    report["failure_module"] = module_name
                    break
                    
            except Exception as e:
                report["results"][module_name] = {
                    "error": str(e),
                    "qa_pass": False
                }
                report["overall_result"] = "ERROR"
                break
        else:
            report["overall_result"] = "PASS"
        
        return report
```

## Sampling Strategy

### Statistical Sampling

```python
class QCSamplingStrategy:
    """Determine which devices to test"""
    
    def __init__(self, batch_size):
        self.batch_size = batch_size
        
        # Sampling rates
        self.rates = {
            "first_article": 1.0,      # 100% of first 5 units
            "basic_test": 1.0,         # 100% basic test
            "functional_test": 0.1,     # 10% functional test
            "stress_test": 0.01,       # 1% stress test
            "destructive_test": 0.001   # 0.1% destructive test
        }
        
    def select_devices_for_testing(self, device_list):
        """Select devices for different test levels"""
        
        selected = {
            "basic": [],
            "functional": [],
            "stress": [],
            "destructive": []
        }
        
        for i, device in enumerate(device_list):
            # First article inspection
            if i < 5:
                selected["stress"].append(device)
            
            # Basic test (all devices)
            selected["basic"].append(device)
            
            # Functional test sampling
            if random.random() < self.rates["functional_test"]:
                selected["functional"].append(device)
            
            # Stress test sampling
            if random.random() < self.rates["stress_test"]:
                selected["stress"].append(device)
            
            # Destructive test sampling
            if random.random() < self.rates["destructive_test"]:
                selected["destructive"].append(device)
        
        return selected
```

## Defect Handling

### Defect Classification

```python
class DefectClassification:
    """Classify and handle defects"""
    
    DEFECT_LEVELS = {
        "CRITICAL": {
            "description": "Safety or security failure",
            "action": "Quarantine entire batch",
            "examples": ["Safety filter bypass", "Encryption failure"]
        },
        "MAJOR": {
            "description": "Function not working",
            "action": "Reject device, investigate",
            "examples": ["Model won't load", "Profile creation fails"]
        },
        "MINOR": {
            "description": "Performance or cosmetic",
            "action": "Rework if possible",
            "examples": ["Slow response", "Label misaligned"]
        }
    }
    
    def classify_defect(self, test_results):
        """Determine defect severity"""
        
        # Critical defects
        if any([
            not test_results.get("safety_active"),
            not test_results.get("encryption_working"),
            test_results.get("safety_bypass_possible")
        ]):
            return "CRITICAL"
        
        # Major defects
        if any([
            not test_results.get("models_available"),
            not test_results.get("launcher_starts"),
            test_results.get("boot_time", 0) > 60
        ]):
            return "MAJOR"
        
        # Minor defects
        if any([
            test_results.get("response_time", 0) > 5,
            test_results.get("cosmetic_issues"),
            test_results.get("documentation_missing")
        ]):
            return "MINOR"
        
        return "PASS"
```

### Corrective Actions

```python
class CorrectiveActions:
    """Handle QC failures"""
    
    def handle_failure(self, device, defect_level, details):
        """Take appropriate action for failures"""
        
        if defect_level == "CRITICAL":
            # Stop production immediately
            self.halt_production()
            
            # Quarantine batch
            self.quarantine_batch(device.batch_id)
            
            # Root cause analysis
            self.initiate_rca(details)
            
            # Notify management
            self.send_critical_alert(details)
            
        elif defect_level == "MAJOR":
            # Isolate device
            self.quarantine_device(device)
            
            # Check if systematic
            if self.is_systematic_issue(device.batch_id, details):
                self.investigate_batch(device.batch_id)
            
            # Attempt rework
            if self.can_rework(device, details):
                self.schedule_rework(device)
            else:
                self.mark_for_disposal(device)
                
        elif defect_level == "MINOR":
            # Log issue
            self.log_minor_defect(device, details)
            
            # Rework if cost-effective
            if self.is_rework_worthwhile(device, details):
                self.schedule_rework(device)
            else:
                self.approve_with_deviation(device)
```

## Documentation

### QC Report Template

```markdown
# Quality Control Report

**Batch ID**: B20250127  
**Date**: 2025-01-27  
**Inspector**: QC Station 1  
**Quantity Tested**: 100 units  

## Summary
- **Pass Rate**: 98%
- **Defects Found**: 2
- **Critical Issues**: 0
- **Rework Required**: 1
- **Rejected**: 1

## Test Results

### Basic Testing (100 units)
- Partition Verification: 100/100 ✓
- Content Integrity: 100/100 ✓
- Read/Write Speed: 99/100 ✓

### Functional Testing (10 units)
- System Boot: 10/10 ✓
- Model Loading: 10/10 ✓
- Safety System: 10/10 ✓
- Profile Creation: 9/10 ⚠️

### Stress Testing (1 unit)
- 10-minute stress: PASS
- Memory usage: Peak 1.2GB
- Success rate: 99.8%

## Defects Log

| Serial | Defect Type | Description | Action |
|--------|------------|-------------|---------|
| B20250127-0451 | MINOR | Slow boot (35s) | Rework |
| B20250127-0782 | MAJOR | Profile creation fails | Reject |

## Recommendations
1. Investigate profile creation issue
2. Monitor boot times in next batch
3. No critical concerns

**Approved By**: _________________  
**Date**: _________________
```

### Traceability

```python
class QCTraceability:
    """Maintain complete QC records"""
    
    def create_device_record(self, device):
        """Create traceable QC record"""
        
        record = {
            "device_id": device.serial_number,
            "batch_id": device.batch_id,
            "manufacture_date": device.manufacture_date,
            "qc_tests": [],
            "qc_results": {},
            "inspector": self.get_inspector_id(),
            "station": self.get_station_id(),
            "timestamp": datetime.now()
        }
        
        # Add test results
        for test_name, test_result in self.test_results.items():
            record["qc_tests"].append({
                "test": test_name,
                "result": test_result,
                "timestamp": datetime.now()
            })
        
        # Generate QC certificate
        record["qc_certificate"] = self.generate_certificate(record)
        
        # Store in database
        self.store_record(record)
        
        # Add QC sticker to device
        self.print_qc_label(device, record["qc_certificate"])
        
        return record
```

## Continuous Improvement

### Metrics Tracking

```python
# Key QC metrics to track

QC_METRICS = {
    "first_pass_yield": "Percentage passing all tests first time",
    "defect_rate": "Defects per million opportunities (DPMO)",
    "cycle_time": "Average time for complete QC",
    "escape_rate": "Defects found by customers",
    "rework_rate": "Percentage requiring rework",
    "scrap_rate": "Percentage scrapped",
    "cost_of_quality": "Total QC cost per unit"
}

def calculate_metrics(batch_results):
    """Calculate QC metrics for batch"""
    
    metrics = {}
    
    total_units = len(batch_results)
    passed_first = sum(1 for r in batch_results if r["first_pass"])
    
    metrics["first_pass_yield"] = (passed_first / total_units) * 100
    metrics["defect_rate"] = calculate_dpmo(batch_results)
    metrics["cycle_time"] = average_test_time(batch_results)
    
    return metrics
```

---

*Quality Control ensures every Sunflower AI device meets our high standards for safety, functionality, and reliability.*
