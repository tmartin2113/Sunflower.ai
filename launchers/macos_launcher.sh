#!/bin/bash

# Sunflower AI Professional System - macOS Launcher
# Version: 6.2.0
# Copyright (c) 2025 Sunflower AI Educational Systems
# Production-Ready Universal Family Launcher with Complete Error Handling

set -euo pipefail
IFS=$'\n\t'

# ==================== SYSTEM CONSTANTS ====================
readonly SYSTEM_VERSION="6.2.0"
readonly MIN_RAM_GB=4
readonly MIN_MACOS_VERSION="10.14"  # Mojave
readonly LAUNCHER_PID=$$
readonly LOG_DIR="${HOME}/Library/Logs/SunflowerAI"
readonly CDROM_MARKER="SUNFLOWER_AI_SYSTEM"
readonly USB_MARKER="SUNFLOWER_USER_DATA"
readonly OLLAMA_PORT=11434
readonly OPENWEBUI_PORT=8080
readonly MAX_RETRY_ATTEMPTS=3
readonly RETRY_DELAY=2

# ==================== ERROR CODES ====================
readonly ERROR_SUCCESS=0
readonly ERROR_INSUFFICIENT_PRIVILEGES=1001
readonly ERROR_CDROM_NOT_FOUND=1002
readonly ERROR_USB_NOT_FOUND=1003
readonly ERROR_INSUFFICIENT_RAM=1004
readonly ERROR_INCOMPATIBLE_OS=1005
readonly ERROR_PYTHON_NOT_FOUND=1006
readonly ERROR_INTEGRITY_CHECK_FAILED=1007
readonly ERROR_OLLAMA_FAILED=1008
readonly ERROR_OPENWEBUI_FAILED=1009
readonly ERROR_MODEL_LOAD_FAILED=1010

# ==================== COLOR CODES ====================
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m' # No Color

# ==================== GLOBAL VARIABLES ====================
CDROM_PATH=""
USB_PATH=""
SELECTED_MODEL=""
MODEL_TIER=""
SYSTEM_RAM_GB=0
CPU_CORES=0
HAS_GPU=0
PERF_SCORE=0
PYTHON_EXE=""
LOG_FILE=""

# ==================== INITIALIZATION ====================
initialize() {
    clear
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║           SUNFLOWER AI PROFESSIONAL SYSTEM v${SYSTEM_VERSION}           ║${NC}"
    echo -e "${CYAN}║              Family-Focused K-12 STEM Education                  ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Starting family setup wizard...${NC}"
    echo ""
    
    # Create log directory
    mkdir -p "${LOG_DIR}"
    readonly LOG_FILE="${LOG_DIR}/launcher_$(date +%Y%m%d_%H%M%S).log"
    
    # Log startup
    log_message "INFO" "Sunflower AI Launcher started - PID: ${LAUNCHER_PID}"
    log_message "INFO" "Version: ${SYSTEM_VERSION}"
    log_message "INFO" "Log file: ${LOG_FILE}"
}

# ==================== LOGGING FUNCTIONS ====================
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[${timestamp}] [${level}] ${message}" >> "${LOG_FILE}"
    
    case ${level} in
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${message}" >&2
            ;;
        WARNING)
            echo -e "${YELLOW}[WARNING]${NC} ${message}"
            ;;
        INFO)
            # Silent for info messages unless verbose
            ;;
        SUCCESS)
            echo -e "${GREEN}[✓]${NC} ${message}"
            ;;
    esac
}

show_user_error() {
    local title=$1
    local message=$2
    
    echo ""
    echo -e "${RED}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                          ERROR DETECTED                          ║${NC}"
    echo -e "${RED}╠══════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${RED}║${NC}  ${title}"
    echo -e "${RED}║${NC}  "
    echo -e "${RED}║${NC}  ${message}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Also show native macOS alert if available
    if command -v osascript >/dev/null 2>&1; then
        osascript -e "display alert \"Sunflower AI Setup Error\" message \"${title}: ${message}\" as critical" 2>/dev/null || true
    fi
    
    log_message "ERROR" "${title}: ${message}"
}

# ==================== SYSTEM VALIDATION ====================
check_admin_privileges() {
    if [[ $EUID -ne 0 ]]; then
        log_message "INFO" "Requesting administrator privileges..."
        
        # Try to re-run with sudo
        if command -v sudo >/dev/null 2>&1; then
            exec sudo "$0" "$@"
            exit $?
        else
            show_user_error "Administrator Required" "Please run this script with administrator privileges"
            return ${ERROR_INSUFFICIENT_PRIVILEGES}
        fi
    fi
    
    log_message "INFO" "Administrator privileges confirmed"
    return 0
}

validate_macos_version() {
    local current_version
    current_version=$(sw_vers -productVersion)
    
    # Convert versions to comparable integers
    local current_major current_minor
    current_major=$(echo "${current_version}" | cut -d. -f1)
    current_minor=$(echo "${current_version}" | cut -d. -f2)
    
    local min_major min_minor
    min_major=$(echo "${MIN_MACOS_VERSION}" | cut -d. -f1)
    min_minor=$(echo "${MIN_MACOS_VERSION}" | cut -d. -f2)
    
    if [[ ${current_major} -lt ${min_major} ]] || \
       [[ ${current_major} -eq ${min_major} && ${current_minor} -lt ${min_minor} ]]; then
        log_message "ERROR" "macOS ${current_version} is below minimum ${MIN_MACOS_VERSION}"
        show_user_error "macOS Version Too Old" "Please update to macOS ${MIN_MACOS_VERSION} or newer"
        return ${ERROR_INCOMPATIBLE_OS}
    fi
    
    log_message "INFO" "macOS ${current_version} meets requirements"
    return 0
}

validate_system_ram() {
    local ram_bytes
    ram_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
    SYSTEM_RAM_GB=$((ram_bytes / 1073741824))
    
    if [[ ${SYSTEM_RAM_GB} -lt ${MIN_RAM_GB} ]]; then
        log_message "ERROR" "System has ${SYSTEM_RAM_GB}GB RAM, minimum is ${MIN_RAM_GB}GB"
        show_user_error "Insufficient Memory" "Your system has ${SYSTEM_RAM_GB}GB RAM. Minimum required: ${MIN_RAM_GB}GB"
        return ${ERROR_INSUFFICIENT_RAM}
    fi
    
    log_message "INFO" "System RAM: ${SYSTEM_RAM_GB}GB - meets requirements"
    return 0
}

# ==================== PARTITION DETECTION ====================
detect_cdrom_partition() {
    CDROM_PATH=""
    
    # Check mounted volumes
    for volume in /Volumes/*; do
        if [[ -f "${volume}/sunflower_cd.id" ]]; then
            # Verify it's read-only (CD-ROM characteristic)
            if ! touch "${volume}/test_write.tmp" 2>/dev/null; then
                CDROM_PATH="${volume}"
                log_message "INFO" "CD-ROM partition found at ${CDROM_PATH}"
                return 0
            fi
        fi
    done
    
    # Check disk images
    for dmg in /Volumes/SunflowerAI*; do
        if [[ -f "${dmg}/sunflower_cd.id" ]]; then
            CDROM_PATH="${dmg}"
            log_message "INFO" "CD-ROM disk image found at ${CDROM_PATH}"
            return 0
        fi
    done
    
    log_message "ERROR" "CD-ROM partition with marker ${CDROM_MARKER} not found"
    return ${ERROR_CDROM_NOT_FOUND}
}

detect_usb_partition() {
    USB_PATH=""
    
    # Check mounted volumes
    for volume in /Volumes/*; do
        if [[ -f "${volume}/sunflower_data.id" ]]; then
            # Verify write permission
            if touch "${volume}/test_write.tmp" 2>/dev/null; then
                rm -f "${volume}/test_write.tmp"
                USB_PATH="${volume}"
                
                # Create required directories
                mkdir -p "${USB_PATH}/profiles"
                mkdir -p "${USB_PATH}/sessions"
                mkdir -p "${USB_PATH}/logs"
                mkdir -p "${USB_PATH}/config"
                mkdir -p "${USB_PATH}/ollama"
                
                log_message "INFO" "USB partition found at ${USB_PATH}"
                return 0
            fi
        fi
    done
    
    # Fallback to user directory
    USB_PATH="${HOME}/.sunflower_ai/data"
    mkdir -p "${USB_PATH}/profiles"
    mkdir -p "${USB_PATH}/sessions"
    mkdir -p "${USB_PATH}/logs"
    mkdir -p "${USB_PATH}/config"
    mkdir -p "${USB_PATH}/ollama"
    
    log_message "WARNING" "USB partition not found, using local directory: ${USB_PATH}"
    return 0
}

# ==================== INTEGRITY VERIFICATION ====================
verify_system_integrity() {
    local manifest_file="${CDROM_PATH}/system/integrity.manifest"
    
    if [[ ! -f "${manifest_file}" ]]; then
        log_message "WARNING" "Integrity manifest not found, skipping verification"
        return 0
    fi
    
    # Verify critical files exist
    local critical_files=(
        "${CDROM_PATH}/system/launcher_common.py"
        "${CDROM_PATH}/system/openwebui_integration.py"
        "${CDROM_PATH}/modelfiles/sunflower-kids.modelfile"
        "${CDROM_PATH}/modelfiles/sunflower-educator.modelfile"
        "${CDROM_PATH}/ollama/ollama"
    )
    
    local missing_files=""
    for file in "${critical_files[@]}"; do
        if [[ ! -f "${file}" ]]; then
            missing_files="${missing_files}\n  - ${file}"
            log_message "ERROR" "Critical file missing: ${file}"
        fi
    done
    
    if [[ -n "${missing_files}" ]]; then
        show_user_error "System Files Missing" "Critical files not found:${missing_files}"
        return ${ERROR_INTEGRITY_CHECK_FAILED}
    fi
    
    # Verify checksums if available
    if command -v shasum >/dev/null 2>&1; then
        while IFS=' ' read -r checksum filepath; do
            if [[ -f "${CDROM_PATH}/${filepath}" ]]; then
                local actual_checksum
                actual_checksum=$(shasum -a 256 "${CDROM_PATH}/${filepath}" 2>/dev/null | cut -d' ' -f1)
                if [[ "${actual_checksum}" != "${checksum}" ]]; then
                    log_message "ERROR" "Checksum mismatch for ${filepath}"
                    return ${ERROR_INTEGRITY_CHECK_FAILED}
                fi
            fi
        done < "${manifest_file}"
    fi
    
    log_message "INFO" "System integrity verification passed"
    return 0
}

# ==================== HARDWARE DETECTION ====================
detect_hardware_capabilities() {
    # Detect CPU information
    CPU_CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo "1")
    local cpu_brand
    cpu_brand=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Unknown")
    
    # Check for Apple Silicon
    local is_apple_silicon=0
    if [[ "${cpu_brand}" == *"Apple"* ]] || [[ "${cpu_brand}" == *"M1"* ]] || [[ "${cpu_brand}" == *"M2"* ]] || [[ "${cpu_brand}" == *"M3"* ]]; then
        is_apple_silicon=1
        HAS_GPU=1  # Apple Silicon has integrated GPU
    else
        # Check for discrete GPU
        HAS_GPU=0
        if system_profiler SPDisplaysDataType 2>/dev/null | grep -q "Chipset Model"; then
            local gpu_info
            gpu_info=$(system_profiler SPDisplaysDataType | grep "Chipset Model" | head -1)
            if [[ "${gpu_info}" == *"AMD"* ]] || [[ "${gpu_info}" == *"NVIDIA"* ]]; then
                HAS_GPU=1
            fi
        fi
    fi
    
    # Calculate performance score
    PERF_SCORE=$((SYSTEM_RAM_GB * 10 + CPU_CORES * 5))
    if [[ ${HAS_GPU} -eq 1 ]]; then
        PERF_SCORE=$((PERF_SCORE + 20))
    fi
    if [[ ${is_apple_silicon} -eq 1 ]]; then
        PERF_SCORE=$((PERF_SCORE + 30))  # Bonus for Apple Silicon efficiency
    fi
    
    log_message "INFO" "Hardware: CPU=${cpu_brand}, Cores=${CPU_CORES}, RAM=${SYSTEM_RAM_GB}GB, GPU=${HAS_GPU}, Apple Silicon=${is_apple_silicon}"
    log_message "INFO" "Performance score: ${PERF_SCORE}"
}

select_optimal_model() {
    # Model selection based on performance score
    if [[ ${PERF_SCORE} -ge 100 ]]; then
        SELECTED_MODEL="llama3.2:7b"
        MODEL_TIER="high"
    elif [[ ${PERF_SCORE} -ge 70 ]]; then
        SELECTED_MODEL="llama3.2:3b"
        MODEL_TIER="medium"
    elif [[ ${PERF_SCORE} -ge 40 ]]; then
        SELECTED_MODEL="llama3.2:1b"
        MODEL_TIER="low"
    else
        SELECTED_MODEL="llama3.2:1b-q4_0"
        MODEL_TIER="minimum"
    fi
    
    log_message "INFO" "Selected model: ${SELECTED_MODEL} (${MODEL_TIER} tier)"
}

# ==================== PYTHON SETUP ====================
setup_python_environment() {
    # Check for Python 3
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_EXE="python3"
    elif command -v python >/dev/null 2>&1; then
        # Check if it's Python 3
        local python_version
        python_version=$(python --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1)
        if [[ ${python_version} -eq 3 ]]; then
            PYTHON_EXE="python"
        fi
    fi
    
    if [[ -z "${PYTHON_EXE}" ]]; then
        log_message "ERROR" "Python 3 not found"
        
        # Suggest installation
        echo -e "${YELLOW}Python 3 is required but not found.${NC}"
        echo -e "${BLUE}You can install it using:${NC}"
        echo -e "  ${WHITE}brew install python3${NC} (if you have Homebrew)"
        echo -e "  ${WHITE}Or download from https://python.org${NC}"
        
        return ${ERROR_PYTHON_NOT_FOUND}
    fi
    
    log_message "INFO" "Python found: ${PYTHON_EXE}"
    
    # Install required packages
    echo -e "${BLUE}Installing required Python packages...${NC}"
    "${PYTHON_EXE}" -m pip install --quiet --upgrade pip 2>/dev/null || true
    
    if [[ -f "${CDROM_PATH}/requirements.txt" ]]; then
        "${PYTHON_EXE}" -m pip install --quiet -r "${CDROM_PATH}/requirements.txt" 2>/dev/null || true
    fi
    
    return 0
}

# ==================== OLLAMA MANAGEMENT ====================
initialize_ollama() {
    log_message "INFO" "Initializing Ollama service..."
    
    # BUG-006 FIX: Comprehensive PID file validation
    local ollama_pid=""
    local pid_file="${USB_PATH}/ollama/ollama.pid"
    
    # Check if Ollama is already running with proper validation
    if [[ -f "${pid_file}" ]] && [[ -r "${pid_file}" ]]; then
        # Read PID with error handling
        ollama_pid=$(cat "${pid_file}" 2>/dev/null || echo "")
        
        # Validate PID is numeric
        if [[ "${ollama_pid}" =~ ^[0-9]+$ ]]; then
            # Check if process is actually running
            if kill -0 "${ollama_pid}" 2>/dev/null; then
                log_message "INFO" "Ollama already running with PID ${ollama_pid}"
                return 0
            else
                log_message "WARNING" "Stale PID file found, removing"
                rm -f "${pid_file}"
            fi
        else
            log_message "WARNING" "Invalid PID in file: ${ollama_pid}"
            rm -f "${pid_file}"
        fi
    fi
    
    # Start Ollama service
    local ollama_exe="${CDROM_PATH}/ollama/ollama"
    if [[ ! -f "${ollama_exe}" ]]; then
        log_message "ERROR" "Ollama executable not found at ${ollama_exe}"
        return ${ERROR_OLLAMA_FAILED}
    fi
    
    # Make executable
    chmod +x "${ollama_exe}" 2>/dev/null || true
    
    # Set Ollama environment
    export OLLAMA_HOST="127.0.0.1:${OLLAMA_PORT}"
    export OLLAMA_MODELS="${USB_PATH}/models"
    
    # Start Ollama in background
    nohup "${ollama_exe}" serve > "${USB_PATH}/logs/ollama.log" 2>&1 &
    local new_pid=$!
    
    # Save PID with validation
    if [[ "${new_pid}" =~ ^[0-9]+$ ]]; then
        echo "${new_pid}" > "${pid_file}"
        log_message "INFO" "Ollama started with PID ${new_pid}"
    else
        log_message "ERROR" "Failed to get valid PID for Ollama"
        return ${ERROR_OLLAMA_FAILED}
    fi
    
    # Wait for Ollama to be ready
    local attempts=0
    while [[ ${attempts} -lt 30 ]]; do
        if curl -s "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1; then
            log_message "INFO" "Ollama service ready"
            load_models
            return $?
        fi
        sleep 1
        attempts=$((attempts + 1))
    done
    
    log_message "ERROR" "Ollama failed to start within timeout"
    return ${ERROR_OLLAMA_FAILED}
}

stop_ollama() {
    # BUG-006 FIX: Safe PID file handling for cleanup
    local pid_file="${USB_PATH}/ollama/ollama.pid"
    
    if [[ -f "${pid_file}" ]] && [[ -r "${pid_file}" ]]; then
        local ollama_pid
        ollama_pid=$(cat "${pid_file}" 2>/dev/null || echo "")
        
        # Validate PID before attempting to kill
        if [[ "${ollama_pid}" =~ ^[0-9]+$ ]]; then
            if kill -0 "${ollama_pid}" 2>/dev/null; then
                log_message "INFO" "Stopping Ollama (PID ${ollama_pid})..."
                kill -TERM "${ollama_pid}" 2>/dev/null || true
                
                # Wait for graceful shutdown
                local wait_count=0
                while [[ ${wait_count} -lt 10 ]] && kill -0 "${ollama_pid}" 2>/dev/null; do
                    sleep 1
                    wait_count=$((wait_count + 1))
                done
                
                # Force kill if still running
                if kill -0 "${ollama_pid}" 2>/dev/null; then
                    kill -KILL "${ollama_pid}" 2>/dev/null || true
                fi
            fi
        fi
        
        rm -f "${pid_file}"
    fi
}

load_models() {
    log_message "INFO" "Loading AI models..."
    
    local ollama_exe="${CDROM_PATH}/ollama/ollama"
    
    # Create Sunflower Kids model
    if [[ -f "${CDROM_PATH}/modelfiles/sunflower-kids.modelfile" ]]; then
        "${ollama_exe}" create sunflower-kids -f "${CDROM_PATH}/modelfiles/sunflower-kids.modelfile" 2>/dev/null
        if [[ $? -eq 0 ]]; then
            log_message "INFO" "Sunflower Kids model loaded"
        else
            log_message "WARNING" "Failed to load Sunflower Kids model"
        fi
    fi
    
    # Create Sunflower Educator model
    if [[ -f "${CDROM_PATH}/modelfiles/sunflower-educator.modelfile" ]]; then
        "${ollama_exe}" create sunflower-educator -f "${CDROM_PATH}/modelfiles/sunflower-educator.modelfile" 2>/dev/null
        if [[ $? -eq 0 ]]; then
            log_message "INFO" "Sunflower Educator model loaded"
        else
            log_message "WARNING" "Failed to load Sunflower Educator model"
        fi
    fi
    
    return 0
}

# ==================== APPLICATION LAUNCH ====================
launch_application() {
    log_message "INFO" "Launching Sunflower AI application..."
    
    # Create launch configuration
    local config_file="${USB_PATH}/config/launch.json"
    cat > "${config_file}" <<EOF
{
    "cdrom_path": "${CDROM_PATH}",
    "usb_path": "${USB_PATH}",
    "selected_model": "${SELECTED_MODEL}",
    "model_tier": "${MODEL_TIER}",
    "ollama_port": ${OLLAMA_PORT},
    "openwebui_port": ${OPENWEBUI_PORT},
    "system_ram": ${SYSTEM_RAM_GB},
    "cpu_cores": ${CPU_CORES},
    "has_gpu": ${HAS_GPU},
    "platform": "macos"
}
EOF
    
    # Launch main application
    "${PYTHON_EXE}" "${CDROM_PATH}/system/launcher_common.py" \
        --config "${config_file}" \
        --platform macos \
        2>&1 | tee -a "${LOG_FILE}"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [[ ${exit_code} -ne 0 ]]; then
        log_message "ERROR" "Application exited with error code ${exit_code}"
        show_user_error "Application Error" "The application encountered an error. Please check the logs."
        return ${exit_code}
    fi
    
    return ${ERROR_SUCCESS}
}

# ==================== CLEANUP ====================
cleanup() {
    log_message "INFO" "Performing cleanup..."
    
    # Stop Ollama service gracefully
    stop_ollama
    
    # Clean temporary files
    rm -f "${USB_PATH}"/*.tmp 2>/dev/null || true
    
    log_message "INFO" "Launcher shutdown complete"
}

# ==================== SIGNAL HANDLERS ====================
trap cleanup EXIT
trap 'echo "Interrupted"; cleanup; exit 130' INT TERM

# ==================== MAIN EXECUTION ====================
main() {
    initialize
    
    echo -e "${CYAN}[SYSTEM VALIDATION]${NC}"
    echo ""
    
    echo "  [1/8] Checking administrator privileges..."
    check_admin_privileges || exit $?
    
    echo "  [2/8] Validating macOS version..."
    validate_macos_version || exit $?
    
    echo "  [3/8] Checking system memory..."
    validate_system_ram || exit $?
    
    echo "  [4/8] Detecting CD-ROM partition..."
    detect_cdrom_partition
    if [[ $? -ne 0 ]]; then
        show_user_error "CD-ROM Not Found" "Please insert the Sunflower AI device"
        exit ${ERROR_CDROM_NOT_FOUND}
    fi
    
    echo "  [5/8] Detecting USB partition..."
    detect_usb_partition
    if [[ $? -ne 0 ]]; then
        show_user_error "USB Not Found" "Cannot find writable partition"
        exit ${ERROR_USB_NOT_FOUND}
    fi
    
    echo "  [6/8] Verifying system integrity..."
    verify_system_integrity || exit $?
    
    echo "  [7/8] Analyzing hardware capabilities..."
    detect_hardware_capabilities
    select_optimal_model
    
    echo "  [8/8] Setting up environment..."
    setup_python_environment || exit $?
    
    echo ""
    echo -e "${GREEN}System validation complete!${NC}"
    echo ""
    echo -e "${CYAN}[INITIALIZING SERVICES]${NC}"
    echo ""
    
    # Initialize Ollama
    initialize_ollama
    if [[ $? -ne 0 ]]; then
        show_user_error "AI Service Failed" "Unable to start Ollama service"
        exit ${ERROR_OLLAMA_FAILED}
    fi
    
    # Launch application
    echo ""
    echo -e "${CYAN}[LAUNCHING APPLICATION]${NC}"
    echo ""
    
    launch_application
    local app_result=$?
    
    if [[ ${app_result} -eq 0 ]]; then
        echo ""
        echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║              Sunflower AI System Ready for Learning!             ║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    fi
    
    return ${app_result}
}

# Run main function
main "$@"
exit $?
