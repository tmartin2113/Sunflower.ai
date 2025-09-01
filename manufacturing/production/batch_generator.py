#!/usr/bin/env python3
"""
Sunflower AI Professional System - Batch Production Generator
Manages high-volume production of partitioned USB devices.

Copyright (c) 2025 Sunflower AI Corporation
Version: 6.2.0
"""

import os
import sys
import json
import time
import shutil
import threading
import queue
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import concurrent.futures
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from __init__ import (
    DeviceSpecification,
    ProductionStage,
    ProductionMetrics,
    ManufacturingError,
    generate_device_id,
    generate_hardware_token,
    load_manufacturing_config,
    logger
)

# Import production modules
from create_iso import ISOCreator
from prepare_usb_partition import USBPartitionManager

@dataclass
class BatchConfiguration:
    """Configuration for a production batch."""
    batch_id: str
    size: int
    platform: str
    model_variant: str
    parallel_workers: int
    output_directory: Path
    quality_control_rate: float
    auto_retry_failures: bool
    max_retries: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'batch_id': self.batch_id,
            'size': self.size,
            'platform': self.platform,
            'model_variant': self.model_variant,
            'parallel_workers': self.parallel_workers,
            'output_directory': str(self.output_directory),
            'quality_control_rate': self.quality_control_rate,
            'auto_retry_failures': self.auto_retry_failures,
            'max_retries': self.max_retries,
            'timestamp': self.timestamp.isoformat()
        }

class ProductionWorker(threading.Thread):
    """Worker thread for parallel device production."""
    
    def __init__(
        self,
        worker_id: int,
        task_queue: queue.Queue,
        result_queue: queue.Queue,
        batch_config: BatchConfiguration,
        metrics: ProductionMetrics
    ):
        """
        Initialize production worker.
        
        Args:
            worker_id: Unique worker identifier
            task_queue: Queue of production tasks
            result_queue: Queue for results
            batch_config: Batch configuration
            metrics: Production metrics tracker
        """
        super().__init__(name=f"Worker-{worker_id}")
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.batch_config = batch_config
        self.metrics = metrics
        self.daemon = True
        self._stop_event = threading.Event()
    
    def run(self):
        """Main worker loop."""
        logger.info(f"Worker {self.worker_id} started")
        
        while not self._stop_event.is_set():
            try:
                # Get task from queue (timeout to check stop event)
                task = self.task_queue.get(timeout=1)
                
                if task is None:  # Poison pill
                    break
                
                # Process the task
                result = self.process_device(task)
                
                # Put result in queue
                self.result_queue.put(result)
                
                # Mark task as done
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {str(e)}")
        
        logger.info(f"Worker {self.worker_id} stopped")
    
    def stop(self):
        """Signal worker to stop."""
        self._stop_event.set()
    
    def process_device(self, device_spec: DeviceSpecification) -> Dict:
        """
        Process a single device.
        
        Args:
            device_spec: Device specification
            
        Returns:
            Result dictionary
        """
        start_time = time.time()
        result = {
            'device_id': device_spec.device_id,
            'worker_id': self.worker_id,
            'success': False,
            'error': None,
            'duration': 0,
            'stages_completed': []
        }
        
        try:
            logger.info(f"Worker {self.worker_id} processing device {device_spec.device_id}")
            
            # Stage 1: Create ISO
            device_spec.production_stage = ProductionStage.PARTITION_CREATION
            iso_path = self.create_iso_partition(device_spec)
            result['stages_completed'].append('iso_creation')
            result['iso_path'] = str(iso_path)
            
            # Stage 2: Prepare USB partition template
            device_spec.production_stage = ProductionStage.FILE_DEPLOYMENT
            usb_template = self.prepare_usb_partition(device_spec)
            result['stages_completed'].append('usb_preparation')
            result['usb_template'] = str(usb_template)
            
            # Stage 3: Validate
            device_spec.production_stage = ProductionStage.VALIDATION
            validation_passed = self.validate_device(device_spec, iso_path, usb_template)
            result['stages_completed'].append('validation')
            result['validation_passed'] = validation_passed
            
            if validation_passed:
                device_spec.production_stage = ProductionStage.COMPLETE
                result['success'] = True
                self.metrics.record_device(device_spec, success=True)
                logger.info(f"Device {device_spec.device_id} completed successfully")
            else:
                raise ManufacturingError(
                    "Validation failed",
                    ProductionStage.VALIDATION,
                    device_spec.device_id
                )
            
        except Exception as e:
            result['error'] = str(e)
            result['success'] = False
            self.metrics.record_device(device_spec, success=False)
            
            if isinstance(e, ManufacturingError):
                self.metrics.record_error(e)
            
            logger.error(f"Device {device_spec.device_id} failed: {str(e)}")
        
        finally:
            result['duration'] = time.time() - start_time
        
        return result
    
    def create_iso_partition(self, device_spec: DeviceSpecification) -> Path:
        """Create ISO partition for device."""
        iso_creator = ISOCreator(self.batch_config.platform)
        
        try:
            # Prepare ISO contents
            iso_creator.prepare_iso_contents(device_spec)
            
            # Create ISO file
            iso_filename = f"{device_spec.device_id}.iso"
            iso_path = self.batch_config.output_directory / 'iso' / iso_filename
            iso_path.parent.mkdir(parents=True, exist_ok=True)
            
            iso_path = iso_creator.create_iso(device_spec, iso_path)
            
            return iso_path
            
        finally:
            iso_creator.cleanup()
    
    def prepare_usb_partition(self, device_spec: DeviceSpecification) -> Path:
        """Prepare USB partition template."""
        usb_manager = USBPartitionManager()
        
        # Create template
        template_dir = usb_manager.prepare_partition_template(device_spec)
        
        # Copy to output directory
        output_dir = self.batch_config.output_directory / 'usb_templates' / device_spec.device_id
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(template_dir, output_dir)
        
        # Clean up temporary template
        shutil.rmtree(template_dir, ignore_errors=True)
        
        return output_dir
    
    def validate_device(
        self,
        device_spec: DeviceSpecification,
        iso_path: Path,
        usb_template: Path
    ) -> bool:
        """
        Validate device components.
        
        Args:
            device_spec: Device specification
            iso_path: Path to ISO file
            usb_template: Path to USB template
            
        Returns:
            True if validation passes
        """
        # Check ISO exists and has correct size
        if not iso_path.exists():
            logger.error(f"ISO file not found: {iso_path}")
            return False
        
        iso_size_mb = iso_path.stat().st_size / (1024 * 1024)
        expected_size_mb = device_spec.cdrom_size_mb
        
        # Allow 10% variance in size
        if abs(iso_size_mb - expected_size_mb) > expected_size_mb * 0.1:
            logger.error(f"ISO size mismatch: {iso_size_mb}MB vs {expected_size_mb}MB expected")
            return False
        
        # Check USB template structure
        required_dirs = ['profiles', 'conversations', 'progress', 'logs', '.config']
        for dir_name in required_dirs:
            dir_path = usb_template / dir_name
            if not dir_path.exists():
                logger.error(f"USB template missing directory: {dir_name}")
                return False
        
        # Verify configuration files
        config_file = usb_template / '.config' / 'partition.json'
        if not config_file.exists():
            logger.error("USB template missing partition config")
            return False
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                if config.get('device_id') != device_spec.device_id:
                    logger.error("Device ID mismatch in config")
                    return False
        except Exception as e:
            logger.error(f"Failed to validate config: {str(e)}
