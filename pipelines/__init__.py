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

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/sunflower_usb/logs/pipeline.log', mode='a'),
        logging.StreamHandler()
    ]
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
    
    def __init__(self, usb_path: str = "/sunflower_usb"):
        """Initialize pipeline orchestrator with partitioned device paths"""
        self.usb_path = Path(usb_path)
        self.pipelines = {}
        self.active_sessions = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Verify USB partition is mounted and writable
        self._verify_usb_partition()
        
        # Initialize pipeline components
        self._initialize_pipelines()
        
        # Load pipeline configuration
        self.config = self._load_configuration()
        
        logger.info("Pipeline orchestrator initialized successfully")
    
    def _verify_usb_partition(self) -> None:
        """Verify USB partition is accessible and create necessary directories"""
        try:
            if not self.usb_path.exists():
                raise RuntimeError(f"USB partition not found at {self.usb_path}")
            
            # Create required directories
            directories = [
                self.usb_path / "profiles",
                self.usb_path / "conversations",
                self.usb_path / "progress",
                self.usb_path / "logs",
                self.usb_path / "achievements",
                self.usb_path / "parent_dashboard"
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                
            # Test write permissions
            test_file = self.usb_path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            
        except Exception as e:
            logger.critical(f"USB partition verification failed: {e}")
            raise RuntimeError(
                "Unable to access the USB storage. Please ensure the Sunflower device "
                "is properly connected and try again."
            )
    
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
        config_path = self.usb_path / "config" / "pipeline_config.json"
        
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
            if config_path.exists():
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
                        return self._generate_safety_response(context), pipeline_results
                
                else:
                    # Process through pipeline
                    result = pipeline.process(context)
                    
                    if isinstance(result, tuple):
                        context, pipeline_data = result
                        pipeline_results[pipeline_name] = pipeline_data
                    else:
                        context = result
                        pipeline_results[pipeline_name] = {"processed": True}
            
            # Mark session as completed
            self.active_sessions[context.session_id] = PipelineStatus.COMPLETED
            
            # Return final response and metadata
            return context.model_response or "Processing completed", pipeline_results
            
        except Exception as e:
            logger.error(f"Pipeline processing error: {e}")
            self.active_sessions[context.session_id] = PipelineStatus.ERROR
            
            return (
                "I encountered an issue processing your request. Let's try again with a different question!",
                {"error": str(e)}
            )
    
    def _generate_safety_response(self, context: PipelineContext) -> str:
        """Generate age-appropriate safety response when content is blocked"""
        age = context.child_age
        
        if age < 8:
            return "That's an interesting question! Let's explore something fun about science instead. What would you like to learn about animals, space, or how things work?"
        elif age < 12:
            return "That topic isn't available in our STEM learning system. How about we explore something exciting like robotics, chemistry experiments, or coding instead?"
        else:
            return "That content falls outside our STEM education focus. I can help you with science, technology, engineering, or mathematics topics. What subject interests you most?"
    
    def get_pipeline_status(self, session_id: str) -> PipelineStatus:
        """Get current status of a pipeline session"""
        return self.active_sessions.get(session_id, PipelineStatus.IDLE)
    
    def shutdown(self) -> None:
        """Gracefully shutdown pipeline orchestrator"""
        try:
            # Wait for active sessions to complete
            active_count = sum(1 for s in self.active_sessions.values() 
                             if s == PipelineStatus.PROCESSING)
            
            if active_count > 0:
                logger.info(f"Waiting for {active_count} active sessions to complete")
            
            # Shutdown executor
            self.executor.shutdown(wait=True, timeout=10)
            
            # Close all pipelines
            for name, pipeline in self.pipelines.items():
                if hasattr(pipeline, 'close'):
                    pipeline.close()
            
            logger.info("Pipeline orchestrator shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Export main components
__all__ = [
    'PipelineOrchestrator',
    'PipelineContext', 
    'PipelineStatus'
]

# Initialize global orchestrator instance
_orchestrator_instance = None

def get_orchestrator(usb_path: str = "/sunflower_usb") -> PipelineOrchestrator:
    """Get or create global orchestrator instance"""
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = PipelineOrchestrator(usb_path)
    
    return _orchestrator_instance
