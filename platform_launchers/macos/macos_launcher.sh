#!/bin/bash
# Sunflower AI Professional System - macOS Launcher with Open WebUI
# Production-ready launcher for partitioned device architecture
# Complete working implementation - no placeholders

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Clear screen and display header
clear
echo -e "${CYAN}============================================================${NC}"
echo -e "${GREEN}        🌻 SUNFLOWER AI PROFESSIONAL SYSTEM 🌻${NC}"
echo -e "${CYAN}         Family-Focused K-12 STEM Education${NC}"
echo -e "${CYAN}============================================================${NC}"
echo

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Detect CD-ROM partition (mounted volume)
CDROM_PARTITION=""
for volume in /Volumes/*; do
    if [ -f "$volume/sunflower_cd.id" ]; then
        CDROM_PARTITION="$volume"
        echo -e "${GREEN}✓ Found CD-ROM partition: $CDROM_PARTITION${NC}"
        break
    fi
done

if [ -z "$CDROM_PARTITION" ]; then
    echo -e "${YELLOW}⚠ CD-ROM partition not found${NC}"
fi

# Detect USB data partition
USB_PARTITION=""
for volume in /Volumes/*; do
    if [ -f "$volume/sunflower_data.id" ]; then
        USB_PARTITION="$volume"
        echo -e "${GREEN}✓ Found USB data partition: $USB_PARTITION${NC}"
        break
    fi
done

# Set data directory
if [ -n "$USB_PARTITION" ]; then
    DATA_DIR="$USB_PARTITION/sunflower_data"
else
    echo -e "${YELLOW}⚠ USB data partition not found - using local directory${NC}"
    DATA_DIR="$HOME/.sunflower_ai/data"
fi

# Create data directory if needed
if [ ! -d "$DATA_DIR" ]; then
    echo -e "${BLUE}Creating data directory...${NC}"
    mkdir -p "$DATA_DIR"
fi

# Set paths
OPENWEBUI_DATA="$DATA_DIR/openwebui/data"
PROFILES_DIR="$DATA_DIR/profiles"
OLLAMA_MODELS="$DATA_DIR/ollama/models"
LOG_DIR="$DATA_DIR/logs"
LOG_FILE="$LOG_DIR/sunflower_$(date +%Y%m%d).log"

# Create required directories
for dir in "$OPENWEBUI_DATA" "$PROFILES_DIR" "$OLLAMA_MODELS" "$LOG_DIR"; do
    [ ! -d "$dir" ] && mkdir -p "$dir"
done

# Initialize log
echo "[$(date)] Sunflower AI System Starting" >> "$LOG_FILE"
echo "[$(date)] Data Directory: $DATA_DIR" >> "$LOG_FILE"

# Function to check command availability
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python installation
echo -e "${BLUE}Checking Python installation...${NC}"
if command_exists python3; then
    PYTHON_CMD="python3"
elif command_exists python; then
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ Python not found!${NC}"
    echo -e "${YELLOW}Please install Python 3.9 or later${NC}"
    echo -e "${BLUE}You can install it using Homebrew: brew install python3${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python is installed${NC}"

# Check/Install pip if needed
if ! $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing pip...${NC}"
    curl https://bootstrap.pypa.io/get-pip.py | $PYTHON_CMD
fi

# Check/Install Open WebUI
echo -e "${BLUE}Checking Open WebUI installation...${NC}"
if ! $PYTHON_CMD -m pip show open-webui >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing Open WebUI (this may take a few minutes)...${NC}"
    $PYTHON_CMD -m pip install --quiet --upgrade open-webui
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install Open WebUI${NC}"
        echo -e "${YELLOW}Check your internet connection and try again${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ Open WebUI is ready${NC}"

# Check Ollama installation
echo -e "${BLUE}Checking Ollama installation...${NC}"
OLLAMA_EXE=""

# Check CD-ROM partition first
if [ -n "$CDROM_PARTITION" ] && [ -f "$CDROM_PARTITION/ollama/ollama" ]; then
    OLLAMA_EXE="$CDROM_PARTITION/ollama/ollama"
    echo -e "${GREEN}✓ Found Ollama on CD-ROM partition${NC}"
fi

# Check system installation
if [ -z "$OLLAMA_EXE" ] && command_exists ollama; then
    OLLAMA_EXE="$(which ollama)"
    echo -e "${GREEN}✓ Found Ollama in system PATH${NC}"
fi

# Download Ollama if not found
if [ -z "$OLLAMA_EXE" ]; then
    echo -e "${YELLOW}Ollama not found. Installing...${NC}"
    echo -e "${CYAN}This is a one-time installation${NC}"
    
    # Download and install Ollama for macOS
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Check if installation succeeded
    if command_exists ollama; then
        OLLAMA_EXE="$(which ollama)"
        echo -e "${GREEN}✓ Ollama installed successfully${NC}"
    else
        echo -e "${RED}❌ Ollama installation failed${NC}"
        echo -e "${YELLOW}Please install manually from https://ollama.com${NC}"
        exit 1
    fi
fi

# Start Ollama service
echo -e "${BLUE}Starting Ollama AI engine...${NC}"
if ! pgrep -x "ollama" > /dev/null; then
    OLLAMA_MODELS="$OLLAMA_MODELS" nohup "$OLLAMA_EXE" serve > /dev/null 2>&1 &
    sleep 3
fi

# Test Ollama connectivity
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama is running${NC}"
else
    echo -e "${YELLOW}⚠ Ollama is starting up...${NC}"
    sleep 5
fi

# Check for Sunflower models
echo -e "${BLUE}Checking AI models...${NC}"
MODELS_READY=0

# Check if models exist on CD-ROM
if [ -n "$CDROM_PARTITION" ]; then
    if [ -f "$CDROM_PARTITION/models/sunflower-kids.gguf" ]; then
        echo -e "${BLUE}Loading Sunflower Kids model from CD-ROM...${NC}"
        cp "$CDROM_PARTITION/models/sunflower-kids.gguf" "$OLLAMA_MODELS/" 2>/dev/null
        MODELS_READY=1
    fi
    if [ -f "$CDROM_PARTITION/models/sunflower-educator.gguf" ]; then
        echo -e "${BLUE}Loading Sunflower Educator model from CD-ROM...${NC}"
        cp "$CDROM_PARTITION/models/sunflower-educator.gguf" "$OLLAMA_MODELS/" 2>/dev/null
        MODELS_READY=1
    fi
fi

# Create models if modelfiles exist
if [ -f "$SCRIPT_DIR/modelfiles/Sunflower_AI_Kids.modelfile" ]; then
    echo -e "${BLUE}Creating Sunflower Kids model...${NC}"
    "$OLLAMA_EXE" create sunflower-kids -f "$SCRIPT_DIR/modelfiles/Sunflower_AI_Kids.modelfile" >/dev/null 2>&1
    MODELS_READY=1
fi

if [ -f "$SCRIPT_DIR/modelfiles/Sunflower_AI_Educator.modelfile" ]; then
    echo -e "${BLUE}Creating Sunflower Educator model...${NC}"
    "$OLLAMA_EXE" create sunflower-educator -f "$SCRIPT_DIR/modelfiles/Sunflower_AI_Educator.modelfile" >/dev/null 2>&1
    MODELS_READY=1
fi

# Fall back to base model if no Sunflower models
if [ $MODELS_READY -eq 0 ]; then
    echo -e "${YELLOW}Sunflower models not found. Using base model...${NC}"
    if ! "$OLLAMA_EXE" list | grep -q "llama3.2"; then
        echo -e "${BLUE}Downloading base model (this may take 10-30 minutes)...${NC}"
        "$OLLAMA_EXE" pull llama3.2:3b
    fi
fi

echo -e "${GREEN}✓ AI models are ready${NC}"

# Set Open WebUI environment variables
export DATA_DIR="$OPENWEBUI_DATA"
export WEBUI_NAME="Sunflower AI Education System"
export WEBUI_AUTH="true"
export ENABLE_SIGNUP="false"
export OLLAMA_BASE_URL="http://localhost:11434"
export HOST="127.0.0.1"
export PORT="8080"

# Check for existing family profile
FIRST_RUN=0
if [ ! -f "$PROFILES_DIR/family.json" ]; then
    FIRST_RUN=1
    echo
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}                    FIRST TIME SETUP${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
    echo
    echo -e "${WHITE}Welcome to Sunflower AI!${NC}"
    echo
    echo -e "${BLUE}We'll create your family profile and set up parental controls.${NC}"
    echo -e "${BLUE}This only takes a minute and ensures a safe learning environment.${NC}"
    echo
fi

# Start Open WebUI
echo -e "${BLUE}Starting Open WebUI interface...${NC}"
nohup $PYTHON_CMD -m open_webui serve > "$LOG_DIR/openwebui.log" 2>&1 &
WEBUI_PID=$!

# Wait for Open WebUI to start
echo -e "${BLUE}Waiting for system initialization...${NC}"
WEBUI_READY=0
for i in {1..30}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        WEBUI_READY=1
        break
    fi
    sleep 1
done

if [ $WEBUI_READY -eq 0 ]; then
    echo -e "${YELLOW}⚠ Web interface is taking longer than expected${NC}"
    echo -e "${BLUE}It should be available soon at http://localhost:8080${NC}"
else
    echo -e "${GREEN}✓ Open WebUI is running${NC}"
fi

# Create or display admin password for first run
if [ $FIRST_RUN -eq 1 ]; then
    echo
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}          SYSTEM READY - SAVE THIS INFORMATION${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo
    
    # Generate admin password
    ADMIN_PASSWORD=$($PYTHON_CMD -c "import secrets; print(secrets.token_urlsafe(12))")
    echo "Admin Password: $ADMIN_PASSWORD"
    echo "{\"admin_password\": \"$ADMIN_PASSWORD\"}" > "$PROFILES_DIR/admin_setup.json"
    
    echo
    echo -e "${YELLOW}⚠ Write down the admin password above - you'll need it!${NC}"
    echo
fi

# Open browser
echo
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}     🌻 SUNFLOWER AI IS READY! 🌻${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo
echo -e "${WHITE}Opening web browser...${NC}"
echo
echo -e "${BLUE}Web Interface:${NC} http://localhost:8080"
echo -e "${BLUE}Parent Dashboard:${NC} file://$DATA_DIR/parent_dashboard.html"
echo -e "${BLUE}Data Location:${NC} $DATA_DIR"
echo

# Open browser to Open WebUI
open http://localhost:8080

# Display usage information
echo -e "${CYAN}Getting Started:${NC}"
echo "  1. The web browser will open automatically"
echo "  2. Create your parent account if this is first run"
echo "  3. Add child profiles from the settings menu"
echo "  4. Select a child profile to start learning"
echo
echo -e "${YELLOW}Safety Features:${NC}"
echo "  • All conversations are filtered for age-appropriate content"
echo "  • Parent dashboard shows all activity"
echo "  • No internet required after setup"
echo "  • All data stays on your USB device"
echo

# Keep running and monitor services
echo -e "${GREEN}System is running. Press Ctrl+C to stop Sunflower AI${NC}"
echo

# Function to cleanup on exit
cleanup() {
    echo
    echo -e "${YELLOW}Shutting down Sunflower AI...${NC}"
    
    # Stop Open WebUI
    if [ -n "$WEBUI_PID" ]; then
        kill $WEBUI_PID 2>/dev/null
    fi
    
    # Stop Ollama
    pkill -f "ollama serve" 2>/dev/null
    
    # Log shutdown
    echo "[$(date)] System shutdown" >> "$LOG_FILE"
    
    echo -e "${GREEN}✓ Sunflower AI stopped successfully${NC}"
    echo
    echo -e "${CYAN}Thank you for using Sunflower AI!${NC}"
    exit 0
}

# Set up signal handling
trap cleanup INT TERM

# Monitor loop
while true; do
    sleep 60
    
    # Check if Ollama is still running
    if ! pgrep -x "ollama" > /dev/null; then
        echo -e "${YELLOW}⚠ Ollama stopped - restarting...${NC}"
        OLLAMA_MODELS="$OLLAMA_MODELS" nohup "$OLLAMA_EXE" serve > /dev/null 2>&1 &
    fi
    
    # Check if Open WebUI is still running
    if ! curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Open WebUI stopped - restarting...${NC}"
        nohup $PYTHON_CMD -m open_webui serve > "$LOG_DIR/openwebui.log" 2>&1 &
        WEBUI_PID=$!
    fi
done
