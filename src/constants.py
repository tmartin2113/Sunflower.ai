"""
Application-wide constants for Sunflower AI
"""

# Application Info
APP_NAME = "Sunflower AI"
WINDOW_TITLE = "Sunflower AI Education System"
ORGANIZATION = "Sunflower AI"

# Version
VERSION = "1.0.0"

# Model Names
MODEL_KIDS = "sunflower-kids"
MODEL_EDUCATOR = "sunflower-educator"

# Age Ranges
MIN_AGE = 2
MAX_AGE = 18
AGE_GROUPS = {
    'toddler': (2, 5),
    'elementary': (6, 8),
    'middle': (9, 12),
    'high': (13, 16),
    'college_prep': (17, 18)
}

# Response Length Guidelines (words)
RESPONSE_LENGTHS = {
    'toddler': (30, 50),
    'elementary': (50, 75),
    'middle': (75, 100),
    'high': (100, 200),
    'college_prep': (200, 300)
}

# Safety Settings
MAX_SAFETY_STRIKES = 3
SAFETY_COOLDOWN_MINUTES = 30
INAPPROPRIATE_TOPICS = [
    'violence', 'weapons', 'drugs', 'adult content',
    'self-harm', 'dangerous activities', 'illegal activities'
]

# Session Settings
SESSION_TIMEOUT_MINUTES = 30
AUTO_SAVE_INTERVAL_SECONDS = 300
MAX_CONVERSATION_HISTORY = 100

# Model Selection
RAM_REQUIREMENTS = {
    'llama3.2:7b': 16 * 1024**3,      # 16GB
    'llama3.2:3b': 8 * 1024**3,       # 8GB
    'llama3.2:1b': 4 * 1024**3,       # 4GB
    'llama3.2:1b-q4_0': 2 * 1024**3,  # 2GB
}

# UI Settings
DEFAULT_FONT_SIZE = 12
MIN_FONT_SIZE = 10
MAX_FONT_SIZE = 24
CHAT_BUBBLE_MAX_WIDTH = 600

# File Paths
PROFILE_DB_NAME = "profiles.db"
CONVERSATION_DB_NAME = "conversations.db"
LOG_FILE_NAME = "sunflower.log"

# Ollama Settings
OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_TIMEOUT = 30  # seconds
MODEL_LOAD_TIMEOUT = 60  # seconds

# Encryption
ENCRYPTION_ITERATIONS = 100000
SALT_SIZE = 32

# Colors (for themes)
COLORS = {
    'primary': '#FFD700',      # Sunflower yellow
    'secondary': '#8B4513',    # Brown
    'success': '#4CAF50',      # Green
    'warning': '#FF9800',      # Orange
    'danger': '#F44336',       # Red
    'info': '#2196F3',         # Blue
    'light': '#F5F5F5',        # Light gray
    'dark': '#212121'          # Dark gray
}

# Window Sizes
MAIN_WINDOW_SIZE = (1200, 800)
LOGIN_DIALOG_SIZE = (400, 500)
PROFILE_DIALOG_SIZE = (500, 600)

# API Endpoints (Ollama)
OLLAMA_ENDPOINTS = {
    'generate': '/api/generate',
    'chat': '/api/chat',
    'tags': '/api/tags',
    'show': '/api/show',
    'pull': '/api/pull',
    'version': '/api/version'
}
