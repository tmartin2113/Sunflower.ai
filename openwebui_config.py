#!/usr/bin/env python3
"""
Sunflower AI Professional System - Open WebUI Configuration Manager
Production-ready configuration and database management for Open WebUI
Version: 6.2 | Platform: Windows/macOS | Architecture: Partitioned CD-ROM + USB
"""

import os
import sys
import json
import sqlite3
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import yaml
import logging

logger = logging.getLogger(__name__)

class OpenWebUIConfig:
    """Enterprise-grade Open WebUI configuration with child safety focus"""
    
    def __init__(self, cdrom_path: Path, usb_path: Path):
        """Initialize Open WebUI configuration manager"""
        self.cdrom_path = Path(cdrom_path)
        self.usb_path = Path(usb_path)
        self.platform = platform.system()
        
        # Configuration paths
        self.webui_data_path = self.usb_path / 'openwebui_data'
        self.webui_config_path = self.webui_data_path / 'config'
        self.webui_db_path = self.webui_data_path / 'webui.db'
        
        # Model paths on CD-ROM
        self.models_path = self.cdrom_path / 'models'
        
        # Initialize directory structure
        self._initialize_structure()
        
        # Load or create configuration
        self.config = self._load_or_create_config()
        
    def _initialize_structure(self):
        """Create Open WebUI directory structure on USB partition"""
        directories = [
            self.webui_data_path,
            self.webui_config_path,
            self.webui_data_path / 'uploads',
            self.webui_data_path / 'cache',
            self.webui_data_path / 'static',
            self.webui_data_path / 'templates'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            if self.platform != "Windows":
                os.chmod(directory, 0o755)
    
    def _load_or_create_config(self) -> Dict[str, Any]:
        """Load or create Open WebUI configuration"""
        config_file = self.webui_config_path / 'config.yaml'
        
        default_config = {
            'version': '6.2',
            'server': {
                'host': '127.0.0.1',
                'port': 8080,
                'workers': 2,
                'timeout': 300,
                'keep_alive': 75
            },
            'security': {
                'enable_signup': False,
                'enable_api_key': False,
                'enable_admin_panel': False,
                'session_secret': os.urandom(32).hex(),
                'cors_origins': ['http://localhost:8080'],
                'csrf_protection': True
            },
            'models': {
                'default_model': 'sunflower-kids:latest',
                'available_models': [
                    'sunflower-kids:latest',
                    'sunflower-educator:latest'
                ],
                'model_settings': {
                    'sunflower-kids:latest': {
                        'temperature': 0.3,
                        'top_p': 0.9,
                        'top_k': 40,
                        'repeat_penalty': 1.1,
                        'seed': 42,
                        'num_ctx': 2048,
                        'num_predict': 200,
                        'stop': ['User:', 'Human:', 'Assistant:']
                    },
                    'sunflower-educator:latest': {
                        'temperature': 0.7,
                        'top_p': 0.95,
                        'top_k': 50,
                        'repeat_penalty': 1.0,
                        'seed': 42,
                        'num_ctx': 4096,
                        'num_predict': 500
                    }
                }
            },
            'ollama': {
                'api_base_url': 'http://127.0.0.1:11434',
                'request_timeout': 120,
                'enable_gpu': self._detect_gpu_capability(),
                'gpu_layers': -1 if self._detect_gpu_capability() else 0
            },
            'ui': {
                'theme': 'sunflower_kids',
                'title': 'Sunflower AI Learning System',
                'show_model_selector': False,
                'enable_chat_history': True,
                'enable_file_upload': False,
                'enable_voice_input': True,
                'enable_code_blocks': True,
                'enable_latex': True,
                'max_message_length': 500,
                'auto_scroll': True,
                'notification_sounds': True
            },
            'features': {
                'enable_web_search': False,
                'enable_image_generation': False,
                'enable_document_upload': False,
                'enable_calculator': True,
                'enable_code_execution': False,
                'enable_markdown': True
            },
            'data': {
                'database_url': f"sqlite:///{self.webui_db_path}",
                'upload_dir': str(self.webui_data_path / 'uploads'),
                'cache_dir': str(self.webui_data_path / 'cache'),
                'log_level': 'INFO',
                'log_file': str(self.webui_data_path / 'openwebui.log')
            },
            'child_safety': {
                'content_filter': 'strict',
                'block_external_links': True,
                'disable_copy_paste': False,
                'session_recording': True,
                'auto_timeout_minutes': 30,
                'require_parent_override': True,
                'safe_search': True,
                'profanity_filter': True
            }
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    if loaded_config:
                        # Merge configurations
                        config = self._deep_merge(default_config, loaded_config)
                    else:
                        config = default_config
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                config = default_config
        else:
            config = default_config
        
        # Save configuration
        self._save_config(config)
        return config
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to YAML file"""
        config_file = self.webui_config_path / 'config.yaml'
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    def _detect_gpu_capability(self) -> bool:
        """Detect if system has GPU acceleration available"""
        try:
            if self.platform == "Windows":
                # Check for NVIDIA GPU
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
            elif self.platform == "Darwin":
                # macOS - check for Metal support
                result = subprocess.run(
                    ['system_profiler', 'SPDisplaysDataType'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return 'Metal' in result.stdout
            return False
        except:
            return False
    
    def initialize_database(self):
        """Initialize Open WebUI database with child-safe defaults"""
        conn = sqlite3.connect(self.webui_db_path)
        cursor = conn.cursor()
        
        try:
            # Users table (simplified for family use)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL,
                    profile_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP,
                    settings TEXT
                )
            ''')
            
            # Chats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    archived BOOLEAN DEFAULT FALSE,
                    shared BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model TEXT,
                    flagged BOOLEAN DEFAULT FALSE,
                    safety_score REAL,
                    FOREIGN KEY (chat_id) REFERENCES chats (id)
                )
            ''')
            
            # Models table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS models (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    model_file TEXT NOT NULL,
                    model_type TEXT,
                    size_bytes INTEGER,
                    quantization TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    settings TEXT
                )
            ''')
            
            # Settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert default settings
            default_settings = [
                ('ui_theme', 'sunflower_kids'),
                ('safety_mode', 'strict'),
                ('session_timeout', '30'),
                ('content_filter', 'enabled'),
                ('parent_controls', 'enabled')
            ]
            
            for key, value in default_settings:
                cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value)
                )
            
            conn.commit()
            logger.info("Open WebUI database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def register_models(self):
        """Register Sunflower AI models with Open WebUI"""
        conn = sqlite3.connect(self.webui_db_path)
        cursor = conn.cursor()
        
        try:
            models_to_register = [
                {
                    'id': 'sunflower-kids-latest',
                    'name': 'sunflower-kids:latest',
                    'model_file': str(self.models_path / 'sunflower-kids-7b.gguf'),
                    'model_type': 'llama',
                    'size_bytes': 4_500_000_000,
                    'quantization': 'Q4_K_M',
                    'settings': json.dumps({
                        'context_length': 2048,
                        'embedding_length': 4096,
                        'parameters': '7B',
                        'family': 'llama3.2',
                        'safety_enhanced': True
                    })
                },
                {
                    'id': 'sunflower-educator-latest',
                    'name': 'sunflower-educator:latest',
                    'model_file': str(self.models_path / 'sunflower-educator-7b.gguf'),
                    'model_type': 'llama',
                    'size_bytes': 4_500_000_000,
                    'quantization': 'Q4_K_M',
                    'settings': json.dumps({
                        'context_length': 4096,
                        'embedding_length': 4096,
                        'parameters': '7B',
                        'family': 'llama3.2',
                        'professional_mode': True
                    })
                }
            ]
            
            # Also register smaller variants for hardware detection
            hardware_variants = [
                ('3b', 1_800_000_000, 'sunflower-kids-3b.gguf'),
                ('1b', 700_000_000, 'sunflower-kids-1b.gguf'),
                ('1b-q4', 500_000_000, 'sunflower-kids-1b-q4_0.gguf')
            ]
            
            for variant, size, filename in hardware_variants:
                models_to_register.append({
                    'id': f'sunflower-kids-{variant}',
                    'name': f'sunflower-kids:{variant}',
                    'model_file': str(self.models_path / filename),
                    'model_type': 'llama',
                    'size_bytes': size,
                    'quantization': 'Q4_0' if 'q4' in variant else 'Q4_K_M',
                    'settings': json.dumps({
                        'context_length': 1024 if variant == '1b-q4' else 2048,
                        'parameters': variant.upper(),
                        'family': 'llama3.2',
                        'safety_enhanced': True
                    })
                })
            
            # Insert models into database
            for model in models_to_register:
                cursor.execute('''
                    INSERT OR REPLACE INTO models 
                    (id, name, model_file, model_type, size_bytes, quantization, settings)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    model['id'], model['name'], model['model_file'],
                    model['model_type'], model['size_bytes'],
                    model['quantization'], model['settings']
                ))
            
            conn.commit()
            logger.info(f"Registered {len(models_to_register)} models with Open WebUI")
            
        except Exception as e:
            logger.error(f"Model registration error: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def create_webui_user(self, username: str, role: str, profile_id: Optional[str] = None) -> str:
        """Create Open WebUI user for child or educator"""
        import uuid
        
        conn = sqlite3.connect(self.webui_db_path)
        cursor = conn.cursor()
        
        try:
            user_id = str(uuid.uuid4())
            
            # User settings based on role
            if role == 'child':
                settings = {
                    'model': 'sunflower-kids:latest',
                    'theme': 'sunflower_kids',
                    'safety_mode': 'maximum',
                    'features': {
                        'file_upload': False,
                        'web_search': False,
                        'code_execution': False
                    }
                }
            else:  # educator
                settings = {
                    'model': 'sunflower-educator:latest',
                    'theme': 'professional',
                    'safety_mode': 'standard',
                    'features': {
                        'file_upload': True,
                        'web_search': True,
                        'code_execution': True
                    }
                }
            
            cursor.execute('''
                INSERT INTO users (id, username, role, profile_id, settings)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, role, profile_id, json.dumps(settings)))
            
            conn.commit()
            logger.info(f"Created Open WebUI user: {username} ({role})")
            return user_id
            
        except Exception as e:
            logger.error(f"User creation error: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def update_child_settings(self, profile_id: str, age: int):
        """Update Open WebUI settings based on child's age"""
        age_configs = {
            'k2': {  # Ages 5-7
                'max_tokens': 50,
                'temperature': 0.3,
                'theme': 'sunflower_kids_simple',
                'font_size': 'large',
                'animations': True,
                'sounds': True
            },
            'elementary': {  # Ages 8-10
                'max_tokens': 75,
                'temperature': 0.4,
                'theme': 'sunflower_kids',
                'font_size': 'medium',
                'animations': True,
                'sounds': True
            },
            'middle': {  # Ages 11-13
                'max_tokens': 125,
                'temperature': 0.5,
                'theme': 'sunflower_teens',
                'font_size': 'medium',
                'animations': False,
                'sounds': False
            },
            'high': {  # Ages 14-17
                'max_tokens': 200,
                'temperature': 0.6,
                'theme': 'sunflower_advanced',
                'font_size': 'normal',
                'animations': False,
                'sounds': False
            }
        }
        
        # Determine age group
        if age <= 7:
            config = age_configs['k2']
        elif age <= 10:
            config = age_configs['elementary']
        elif age <= 13:
            config = age_configs['middle']
        else:
            config = age_configs['high']
        
        # Update model settings
        model_key = 'sunflower-kids:latest'
        self.config['models']['model_settings'][model_key].update({
            'num_predict': config['max_tokens'],
            'temperature': config['temperature']
        })
        
        # Update UI settings
        self.config['ui'].update({
            'theme': config['theme'],
            'font_size': config['font_size'],
            'enable_animations': config['animations'],
            'notification_sounds': config['sounds']
        })
        
        # Save updated configuration
        self._save_config(self.config)
        
        logger.info(f"Updated settings for profile {profile_id} (age {age})")
    
    def generate_env_file(self) -> Path:
        """Generate .env file for Open WebUI"""
        env_file = self.webui_config_path / '.env'
        
        env_content = f"""# Sunflower AI Open WebUI Environment Configuration
# Generated: {datetime.now().isoformat()}

# Server Configuration
HOST={self.config['server']['host']}
PORT={self.config['server']['port']}
WORKERS={self.config['server']['workers']}
TIMEOUT={self.config['server']['timeout']}

# Security
ENABLE_SIGNUP={str(self.config['security']['enable_signup']).lower()}
ENABLE_API_KEY={str(self.config['security']['enable_api_key']).lower()}
SESSION_SECRET={self.config['security']['session_secret']}
CSRF_PROTECTION={str(self.config['security']['csrf_protection']).lower()}

# Ollama Configuration
OLLAMA_API_BASE_URL={self.config['ollama']['api_base_url']}
OLLAMA_REQUEST_TIMEOUT={self.config['ollama']['request_timeout']}
ENABLE_GPU={str(self.config['ollama']['enable_gpu']).lower()}
GPU_LAYERS={self.config['ollama']['gpu_layers']}

# Data Paths
DATABASE_URL={self.config['data']['database_url']}
UPLOAD_DIR={self.config['data']['upload_dir']}
CACHE_DIR={self.config['data']['cache_dir']}
LOG_LEVEL={self.config['data']['log_level']}
LOG_FILE={self.config['data']['log_file']}

# UI Configuration
UI_THEME={self.config['ui']['theme']}
UI_TITLE={self.config['ui']['title']}
SHOW_MODEL_SELECTOR={str(self.config['ui']['show_model_selector']).lower()}
ENABLE_CHAT_HISTORY={str(self.config['ui']['enable_chat_history']).lower()}

# Child Safety
CONTENT_FILTER={self.config['child_safety']['content_filter']}
BLOCK_EXTERNAL_LINKS={str(self.config['child_safety']['block_external_links']).lower()}
SESSION_RECORDING={str(self.config['child_safety']['session_recording']).lower()}
AUTO_TIMEOUT_MINUTES={self.config['child_safety']['auto_timeout_minutes']}
SAFE_SEARCH={str(self.config['child_safety']['safe_search']).lower()}
PROFANITY_FILTER={str(self.config['child_safety']['profanity_filter']).lower()}

# Default Model
DEFAULT_MODEL={self.config['models']['default_model']}
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        logger.info(f"Generated .env file at {env_file}")
        return env_file
    
    def validate_configuration(self) -> List[str]:
        """Validate Open WebUI configuration for production readiness"""
        issues = []
        
        # Check required paths exist
        if not self.models_path.exists():
            issues.append(f"Models directory not found: {self.models_path}")
        
        # Check model files exist
        for model_name in self.config['models']['available_models']:
            model_id = model_name.replace(':', '-')
            possible_files = [
                self.models_path / f"{model_id}.gguf",
                self.models_path / f"{model_id.split('-')[0]}-7b.gguf"
            ]
            if not any(f.exists() for f in possible_files):
                issues.append(f"Model file not found for: {model_name}")
        
        # Validate security settings
        if self.config['security']['enable_signup']:
            issues.append("User signup should be disabled for family use")
        
        if self.config['security']['enable_api_key']:
            issues.append("API key authentication should be disabled for family use")
        
        # Validate child safety settings
        if self.config['child_safety']['content_filter'] != 'strict':
            issues.append("Content filter must be set to 'strict' for child safety")
        
        if not self.config['child_safety']['session_recording']:
            issues.append("Session recording must be enabled for parent monitoring")
        
        # Check database
        if not self.webui_db_path.exists():
            issues.append("Open WebUI database not initialized")
        
        return issues
    
    def export_configuration(self, output_path: Path):
        """Export complete configuration for backup"""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'version': self.config['version'],
            'platform': self.platform,
            'configuration': self.config,
            'paths': {
                'cdrom': str(self.cdrom_path),
                'usb': str(self.usb_path),
                'webui_data': str(self.webui_data_path),
                'models': str(self.models_path)
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Configuration exported to {output_path}")

# Production utilities
def detect_hardware_capabilities() -> Dict[str, Any]:
    """Detect system hardware for model selection"""
    import psutil
    
    capabilities = {
        'ram_gb': psutil.virtual_memory().total / (1024**3),
        'cpu_cores': psutil.cpu_count(),
        'platform': platform.system(),
        'architecture': platform.machine(),
        'gpu_available': False,
        'recommended_model': 'sunflower-kids:1b-q4'
    }
    
    # GPU detection
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                capabilities['gpu_available'] = True
                capabilities['gpu_memory_mb'] = int(result.stdout.strip())
        except:
            pass
    elif platform.system() == "Darwin":
        # macOS Metal support
        capabilities['gpu_available'] = True
        capabilities['gpu_type'] = 'metal'
    
    # Recommend model based on capabilities
    if capabilities['ram_gb'] >= 16 and capabilities['gpu_available']:
        capabilities['recommended_model'] = 'sunflower-kids:latest'  # 7B model
    elif capabilities['ram_gb'] >= 8:
        capabilities['recommended_model'] = 'sunflower-kids:3b'
    elif capabilities['ram_gb'] >= 4:
        capabilities['recommended_model'] = 'sunflower-kids:1b'
    else:
        capabilities['recommended_model'] = 'sunflower-kids:1b-q4'
    
    return capabilities

if __name__ == "__main__":
    # Example usage
    cdrom = Path("/Volumes/SUNFLOWER_SYSTEM")
    usb = Path("/Volumes/SUNFLOWER_DATA")
    
    config_manager = OpenWebUIConfig(cdrom, usb)
    
    # Initialize database
    config_manager.initialize_database()
    
    # Register models
    config_manager.register_models()
    
    # Generate environment file
    config_manager.generate_env_file()
    
    # Validate configuration
    issues = config_manager.validate_configuration()
    if issues:
        print("Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Configuration validated successfully")
    
    # Detect hardware
    hw = detect_hardware_capabilities()
    print(f"Hardware: {hw['ram_gb']:.1f}GB RAM, Recommended model: {hw['recommended_model']}")
