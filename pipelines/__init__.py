"""
Sunflower AI Professional System - Pipeline Package
Production-ready pipeline orchestration for family-focused K-12 STEM education
Version: 6.2 | Platform: Windows + macOS | Architecture: Partitioned CD-ROM + USB
"""

import os
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from dataclasses import dataclass, asdict
from enum import Enum

# Import standardized path configuration
from config.path_config import get_usb_path, ensure_paths_available

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineStatus(Enum):
    """Pipeline execution status states"""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    SAFETY_BLOCKED = "safety_blocked"

@dataclass
class PipelineContext:
    """Context object passed through pipeline stages"""
    session_id: str
    profile_id: str
    child_name: str
    child_age: int
    grade_level: str
    input_text: str
    model_response: Optional[str] = None
    safety_flags: List[str] = None
    metadata: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.safety_flags is None:
            self.safety_flags = []
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

class PipelineOrchestrator:
    """Central orchestrator for all pipeline operations"""
    
    def __init__(self):
        """Initialize pipeline orchestrator with partitioned device paths"""
        # Ensure paths are available
        if not ensure_paths_available():
            raise RuntimeError(
                "Unable to access Sunflower AI partitions. Please ensure the device "
                "is properly connected and both partitions are mounted."
            )
        
        # Get USB path dynamically
        self.usb_path = get_usb_path()
        if not self.usb_path:
            raise RuntimeError("USB partition not detected")
        
        # Set up logging to USB partition
        log_dir = get_usb_path('logs')
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / 'pipeline.log'
            
            # Add file handler to logger
            file_handler = logging.FileHandler(log_file, mode='a')
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            logger.addHandler(file_handler)
        
        self.pipelines = {}
        self.active_sessions = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize pipeline components
        self._initialize_pipelines()
        
        # Load pipeline configuration
        self.config = self._load_configuration()
        
        logger.info("Pipeline orchestrator initialized successfully")
    
    def _initialize_pipelines(self) -> None:
        """Initialize all pipeline components"""
        try:
            # Import pipeline components
            from pipelines.safety.content_filter import ContentFilterPipeline
            from pipelines.safety.age_adapter import AgeAdapterPipeline
            from pipelines.safety.parent_logger import ParentLoggerPipeline
            from pipelines.education.stem_tutor import STEMTutorPipeline
            from pipelines.education.progress_tracker import ProgressTrackerPipeline
            from pipelines.education.achievement_system import AchievementSystemPipeline
            
            # Initialize safety pipelines (critical priority)
            self.pipelines['content_filter'] = ContentFilterPipeline(self.usb_path)
            self.pipelines['age_adapter'] = AgeAdapterPipeline(self.usb_path)
            self.pipelines['parent_logger'] = ParentLoggerPipeline(self.usb_path)
            
            # Initialize education pipelines
            self.pipelines['stem_tutor'] = STEMTutorPipeline(self.usb_path)
            self.pipelines['progress_tracker'] = ProgressTrackerPipeline(self.usb_path)
            self.pipelines['achievement_system'] = AchievementSystemPipeline(self.usb_path)
            
            logger.info(f"Initialized {len(self.pipelines)} pipeline components")
            
        except ImportError as e:
            logger.error(f"Failed to import pipeline component: {e}")
            raise RuntimeError(
                "System initialization failed. Please restart the Sunflower application."
            )
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load pipeline configuration from USB partition"""
        config_path = get_usb_path('config') / "pipeline_config.json"
        
        default_config = {
            "safety_level": "maximum",
            "response_timeout": 30,
            "max_conversation_length": 100,
            "enable_achievements": True,
            "log_conversations": True,
            "pipeline_order": [
                "content_filter",
                "age_adapter", 
                "stem_tutor",
                "progress_tracker",
                "achievement_system",
                "parent_logger"
            ]
        }
        
        try:
            if config_path and config_path.exists():
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
        except Exception as e:
            logger.warning(f"Using default configuration: {e}")
        
        return default_config
    
    def process_interaction(self, context: PipelineContext) -> Tuple[str, Dict[str, Any]]:
        """
        Process user interaction through all pipeline stages
        Returns: (processed_response, pipeline_metadata)
        """
        with self.lock:
            self.active_sessions[context.session_id] = PipelineStatus.PROCESSING
        
        try:
            # Execute pipelines in configured order
            pipeline_results = {}
            
            for pipeline_name in self.config['pipeline_order']:
                if pipeline_name not in self.pipelines:
                    logger.warning(f"Pipeline {pipeline_name} not found, skipping")
                    continue
                
                pipeline = self.pipelines[pipeline_name]
                
                # Safety pipelines can block execution
                if pipeline_name == 'content_filter':
                    is_safe, context = pipeline.process(context)
                    pipeline_results[pipeline_name] = {"safe": is_safe}
                    
                    if not is_safe:
                        self.active_sessions[context.session_id] = PipelineStatus.SAFETY_BLOCKED
                        return context.model_response, pipeline_results
                else:
                    # Process through pipeline
                    context = pipeline.process(context)
                    pipeline_results[pipeline_name] = {"processed": True}
            
            # Update session status
            with self.lock:
                self.active_sessions[context.session_id] = PipelineStatus.COMPLETED
            
            return context.model_response, pipeline_results
            
        except Exception as e:
            logger.error(f"Pipeline processing error: {e}")
            with self.lock:
                self.active_sessions[context.session_id] = PipelineStatus.ERROR
            raise
    
    def get_session_status(self, session_id: str) -> Optional[PipelineStatus]:
        """Get current status of a session"""
        with self.lock:
            return self.active_sessions.get(session_id)
    
    def cleanup_session(self, session_id: str):
        """Clean up session data"""
        with self.lock:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get statistics for all pipelines"""
        stats = {
            'active_sessions': len(self.active_sessions),
            'pipelines_loaded': len(self.pipelines),
            'pipeline_names': list(self.pipelines.keys()),
            'config': self.config
        }
        
        # Get stats from each pipeline
        for name, pipeline in self.pipelines.items():
            if hasattr(pipeline, 'get_stats'):
                stats[f'{name}_stats'] = pipeline.get_stats()
        
        return stats
    
    def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        logger.info("Shutting down pipeline orchestrator")
        
        # Clean up all sessions
        with self.lock:
            self.active_sessions.clear()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        # Clean up pipelines
        for pipeline in self.pipelines.values():
            if hasattr(pipeline, 'shutdown'):
                pipeline.shutdown()
        
        logger.info("Pipeline orchestrator shutdown complete")


# Global orchestrator instance
_orchestrator_instance = None

def get_orchestrator() -> PipelineOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = PipelineOrchestrator()
    
    return _orchestrator_instance

def shutdown_orchestrator():
    """Shutdown the global orchestrator"""
    global _orchestrator_instance
    
    if _orchestrator_instance:
        _orchestrator_instance.shutdown()
        _orchestrator_instance = None
