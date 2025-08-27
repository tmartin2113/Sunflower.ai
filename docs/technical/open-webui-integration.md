# Open WebUI Integration Documentation

## Overview

Sunflower AI Professional leverages Open WebUI as its user interface layer, providing a familiar, modern chat experience while maintaining complete offline operation and family safety features.

## Integration Architecture

```
┌──────────────────────────────────────┐
│         Sunflower AI Wrapper         │
│    (Safety + Family Management)      │
├──────────────────────────────────────┤
│            Open WebUI                │
│    (Modified for Education)          │
├──────────────────────────────────────┤
│           Ollama Service             │
│     (Local Model Serving)            │
├──────────────────────────────────────┤
│        Custom Modelfiles             │
│   (Sunflower Kids & Educator)        │
└──────────────────────────────────────┘
```

## Open WebUI Modifications

### Core Changes

```python
# Changes made to Open WebUI for Sunflower AI

1. Authentication System:
   - Replaced with family profile system
   - Parent password protection
   - Child avatar selection
   - No email/username required

2. Model Selection:
   - Limited to Sunflower models only
   - Automatic selection based on profile
   - Hidden from child view
   - Parent override available

3. Safety Middleware:
   - Injected before model processing
   - Injected after response generation
   - Real-time content filtering
   - Topic redirection system

4. UI Customization:
   - Age-appropriate themes
   - Simplified interface for young users
   - Removed advanced features
   - Added parent dashboard button
```

### File Structure

```
openwebui/
├── backend/
│   ├── apps/
│   │   ├── ollama/       # Modified for Sunflower models
│   │   ├── webui/        # Family profile integration
│   │   └── socket/       # Real-time safety filtering
│   ├── config.py         # Sunflower-specific config
│   └── main.py           # Entry point modifications
├── static/               # Pre-built UI
└── sunflower/           # Our additions
    ├── safety.py        # Safety middleware
    ├── profiles.py      # Profile management
    └── monitoring.py    # Parent dashboard
```

## Integration Points

### 1. Startup Sequence

```python
def start_sunflower_ai():
    """Initialize all services in correct order"""
    
    # 1. Detect partitions
    cdrom = detect_cdrom_partition()
    usb = detect_usb_partition()
    
    # 2. Start Ollama service
    start_ollama_service()
    
    # 3. Load Sunflower models
    load_model("sunflower-kids")
    load_model("sunflower-educator")
    
    # 4. Configure Open WebUI
    configure_openwebui({
        "auth": False,
        "signup": False,
        "models": ["sunflower-kids", "sunflower-educator"],
        "safety": True,
        "family_mode": True
    })
    
    # 5. Start Open WebUI
    start_openwebui_server(port=8080)
    
    # 6. Launch browser
    webbrowser.open("http://localhost:8080")
```

### 2. Safety Middleware Integration

```python
# Injected into Open WebUI request pipeline

class SunflowerSafetyMiddleware:
    def __init__(self, app):
        self.app = app
        self.safety_filter = ContentFilter()
        self.profile_manager = ProfileManager()
    
    async def __call__(self, request, call_next):
        # Pre-processing
        if request.url.path.startswith("/api/chat"):
            body = await request.body()
            profile = self.profile_manager.get_current()
            
            # Safety check input
            safe_input = self.safety_filter.check_input(
                body.decode(),
                profile.age
            )
            
            if safe_input.blocked:
                return JSONResponse({
                    "response": safe_input.redirect_message,
                    "safety_triggered": True
                })
        
        # Process request
        response = await call_next(request)
        
        # Post-processing
        if response.status_code == 200:
            body = await response.body()
            safe_output = self.safety_filter.check_output(
                body.decode(),
                profile.age
            )
            
            # Log for parents
            self.profile_manager.log_interaction(
                profile.id,
                safe_input.original,
                safe_output.filtered
            )
            
            return Response(safe_output.filtered)
        
        return response
```

### 3. Profile System Integration

```python
# Replace Open WebUI user system with family profiles

class FamilyProfileAuth:
    """Custom authentication for family profiles"""
    
    def __init__(self, usb_partition):
        self.usb_partition = usb_partition
        self.profiles_dir = usb_partition / "profiles"
    
    def authenticate_parent(self, password):
        """Verify parent password"""
        stored_hash = self.load_parent_hash()
        return verify_password(password, stored_hash)
    
    def select_child_profile(self, profile_id):
        """Load child profile for session"""
        profile = self.load_profile(profile_id)
        
        # Configure Open WebUI for this child
        config = {
            "user_id": profile.id,
            "display_name": profile.name,
            "avatar": profile.avatar,
            "model": self.get_model_for_age(profile.age),
            "safety_level": self.get_safety_level(profile.age),
            "ui_theme": self.get_theme_for_age(profile.age)
        }
        
        return config
    
    def get_model_for_age(self, age):
        """Select appropriate model"""
        if age <= 13:
            return "sunflower-kids"
        else:
            return "sunflower-educator"
```

### 4. Model Configuration

```python
# Configure Ollama models for Open WebUI

SUNFLOWER_MODELS = {
    "sunflower-kids": {
        "base_model": "llama3.2:3b",
        "modelfile": "modelfiles/Sunflower_AI_Kids.modelfile",
        "parameters": {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 200,
            "stop": ["User:", "Human:", "Child:"]
        },
        "context_window": 4096
    },
    "sunflower-educator": {
        "base_model": "llama3.2:3b",
        "modelfile": "modelfiles/Sunflower_AI_Educator.modelfile",
        "parameters": {
            "temperature": 0.8,
            "top_p": 0.95,
            "max_tokens": 500,
            "stop": ["User:", "Human:", "Parent:"]
        },
        "context_window": 8192
    }
}

def load_sunflower_models():
    """Load custom models into Ollama"""
    for model_name, config in SUNFLOWER_MODELS.items():
        # Create model from modelfile
        subprocess.run([
            "ollama", "create",
            model_name,
            "-f", config["modelfile"]
        ])
        
        # Verify model loaded
        result = subprocess.run([
            "ollama", "list"
        ], capture_output=True, text=True)
        
        if model_name not in result.stdout:
            raise Exception(f"Failed to load {model_name}")
```

## API Modifications

### Disabled Endpoints

```python
# These Open WebUI endpoints are disabled for safety

DISABLED_ENDPOINTS = [
    "/api/auth/signup",       # No signup needed
    "/api/auth/signin",       # Custom family auth
    "/api/models/pull",       # No model downloads
    "/api/models/delete",     # No model deletion
    "/api/settings/models",   # No model changes
    "/api/documents",         # No document upload
    "/api/images",           # No image generation
    "/api/web_search",       # No internet access
    "/api/admin",           # No admin panel
]
```

### Custom Endpoints

```python
# Added for Sunflower AI functionality

CUSTOM_ENDPOINTS = {
    "/api/family/profiles": "List all family profiles",
    "/api/family/select": "Select active child profile",
    "/api/family/create": "Create new child profile",
    "/api/parent/dashboard": "Access parent dashboard",
    "/api/parent/history": "View conversation history",
    "/api/safety/report": "View safety incidents",
    "/api/progress/stats": "Get learning statistics",
}
```

## UI Customization

### Age-Based Themes

```css
/* Young Learners (5-7) */
.theme-young {
    --primary-color: #FFD700;  /* Bright gold */
    --font-size: 18px;
    --button-size: 64px;
    --avatar-size: 80px;
    --message-padding: 20px;
    --animation-speed: 0.5s;
}

/* Elementary (8-10) */
.theme-elementary {
    --primary-color: #4CAF50;  /* Green */
    --font-size: 16px;
    --button-size: 48px;
    --avatar-size: 60px;
    --message-padding: 15px;
    --animation-speed: 0.3s;
}

/* Middle School (11-13) */
.theme-middle {
    --primary-color: #2196F3;  /* Blue */
    --font-size: 14px;
    --button-size: 40px;
    --avatar-size: 50px;
    --message-padding: 12px;
    --animation-speed: 0.2s;
}

/* High School (14-17) */
.theme-high {
    --primary-color: #9C27B0;  /* Purple */
    --font-size: 14px;
    --button-size: 36px;
    --avatar-size: 40px;
    --message-padding: 10px;
    --animation-speed: 0.1s;
}
```

### Hidden Features

```javascript
// Features hidden from child view
const HIDDEN_FEATURES = [
    '#model-selector',
    '#settings-advanced',
    '#system-prompt-editor',
    '#api-keys-section',
    '#admin-panel-link',
    '#document-upload',
    '#web-search-toggle',
    '#voice-input',  // Hidden for young children
    '#export-chat',  // Parent-only feature
];

function hideAdvancedFeatures(age) {
    HIDDEN_FEATURES.forEach(selector => {
        const element = document.querySelector(selector);
        if (element) {
            element.style.display = 'none';
        }
    });
    
    // Show age-appropriate features
    if (age >= 14) {
        document.querySelector('#export-chat').style.display = 'block';
    }
    if (age >= 11) {
        document.querySelector('#voice-input').style.display = 'block';
    }
}
```

## Session Management

### Profile Sessions

```python
class ProfileSessionManager:
    """Manage child sessions in Open WebUI"""
    
    def __init__(self):
        self.active_sessions = {}
        self.session_timeout = 3600  # 1 hour
    
    def create_session(self, profile_id):
        """Create new child session"""
        session = {
            "id": generate_session_id(),
            "profile_id": profile_id,
            "started_at": datetime.now(),
            "last_activity": datetime.now(),
            "messages_count": 0,
            "topics_explored": [],
            "safety_incidents": 0
        }
        
        self.active_sessions[session["id"]] = session
        
        # Configure Open WebUI for this session
        self.configure_webui_session(session)
        
        return session["id"]
    
    def configure_webui_session(self, session):
        """Apply profile settings to Open WebUI"""
        profile = self.load_profile(session["profile_id"])
        
        # Set model
        os.environ["OLLAMA_MODEL"] = self.get_model_for_profile(profile)
        
        # Set safety level
        os.environ["SAFETY_LEVEL"] = str(self.get_safety_level(profile.age))
        
        # Set UI theme
        os.environ["UI_THEME"] = self.get_theme_for_age(profile.age)
        
        # Set response limits
        os.environ["MAX_TOKENS"] = str(self.get_token_limit(profile.age))
```

## Error Handling

### Graceful Failures

```python
class OpenWebUIErrorHandler:
    """Handle Open WebUI failures gracefully"""
    
    def handle_model_error(self, error):
        """Model loading or response error"""
        if "out of memory" in str(error):
            # Try smaller model
            return self.fallback_to_smaller_model()
        elif "model not found" in str(error):
            # Reload model
            return self.reload_model()
        else:
            # Generic error message for child
            return {
                "response": "I need to think about that differently. Can you try asking in another way?",
                "error_logged": True
            }
    
    def handle_service_error(self, error):
        """Open WebUI service error"""
        if self.is_port_conflict(error):
            # Try alternative port
            return self.start_on_alternative_port()
        elif self.is_permission_error(error):
            # Prompt for admin
            return self.prompt_admin_permission()
        else:
            # Restart services
            return self.restart_all_services()
```

## Performance Optimization

### Caching Strategy

```python
# Cache frequently used data
CACHE_CONFIG = {
    "profile_cache": {
        "enabled": True,
        "ttl": 3600,
        "max_size": 100
    },
    "response_cache": {
        "enabled": True,
        "ttl": 300,
        "max_size": 1000
    },
    "model_cache": {
        "enabled": True,
        "persistent": True,
        "location": "/usb_partition/cache/models"
    }
}
```

### Resource Management

```python
def optimize_for_hardware():
    """Adjust Open WebUI for available resources"""
    
    ram_gb = get_available_ram_gb()
    
    if ram_gb >= 16:
        config = {
            "max_workers": 4,
            "context_window": 8192,
            "batch_size": 8,
            "cache_size": "2GB"
        }
    elif ram_gb >= 8:
        config = {
            "max_workers": 2,
            "context_window": 4096,
            "batch_size": 4,
            "cache_size": "1GB"
        }
    else:  # 4GB minimum
        config = {
            "max_workers": 1,
            "context_window": 2048,
            "batch_size": 1,
            "cache_size": "512MB"
        }
    
    apply_config_to_openwebui(config)
```

## Debugging Integration

### Logging

```python
# Comprehensive logging for troubleshooting

import logging

# Configure loggers
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/usb_partition/logs/integration.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('sunflower.integration')

# Log integration events
logger.info("Starting Open WebUI integration")
logger.debug(f"Profile selected: {profile_id}")
logger.warning(f"Safety filter triggered: {topic}")
logger.error(f"Failed to load model: {error}")
```

### Health Checks

```python
def check_integration_health():
    """Verify all integration points working"""
    
    checks = {
        "ollama_service": check_ollama_running(),
        "models_loaded": check_models_available(),
        "openwebui_service": check_openwebui_responding(),
        "safety_middleware": check_safety_active(),
        "profile_system": check_profiles_accessible(),
        "parent_dashboard": check_dashboard_available()
    }
    
    return all(checks.values()), checks
```

## Maintenance

### Updating Open WebUI

```bash
# Process for updating Open WebUI component

1. Download new Open WebUI version
2. Test with Sunflower modifications
3. Apply custom patches:
   - Family authentication
   - Safety middleware
   - UI customizations
4. Bundle with new USB device version
5. No automatic updates (by design)
```

### Troubleshooting Integration

| Issue | Check | Solution |
|-------|-------|----------|
| WebUI won't start | Port availability | Change port or kill process |
| Models not showing | Ollama connection | Restart Ollama service |
| Safety not working | Middleware loaded | Check integration.log |
| Profiles not loading | USB partition | Verify write permissions |
| UI looks wrong | Theme application | Clear browser cache |

---

*This integration provides a seamless, safe, and educational experience by combining Open WebUI's interface with Sunflower AI's safety and family features.*
