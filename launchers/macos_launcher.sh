#!/bin/bash

# Sunflower AI Professional System - macOS Launcher
# Version: 6.2.0
# Copyright (c) 2025 Sunflower AI Educational Systems
# Production-Ready Universal Family Launcher

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

# ==================== ERROR CODES ====================
readonly ERROR_INSUFFICIENT_PRIVILEGES=1001
readonly ERROR_CDROM_NOT_FOUND=1002
readonly ERROR_USB_NOT_FOUND=1003
readonly ERROR_INSUFFICIENT_RAM=1004
readonly ERROR_INCOMPATIBLE_OS=1005
readonly ERROR_PYTHON_NOT_FOUND=1006
readonly ERROR_INTEGRITY_CHECK_FAILED=1007

# ==================== COLOR CODES ====================
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
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

# ==================== INITIALIZATION ====================
initialize() {
    clear
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║           SUNFLOWER AI PROFESSIONAL SYSTEM v${SYSTEM_VERSION}                ║${NC}"
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
}

# ==================== LOGGING FUNCTIONS ====================
log_message() {
    local level=$1
    local message=$2
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] ${message}" >> "${LOG_FILE}"
    
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
    
    # Also show native macOS alert
    osascript -e "display alert \"Sunflower AI Setup Error\" message \"${title}: ${message}\" as critical"
}

# ==================== SYSTEM VALIDATION ====================
check_admin_privileges() {
    if [[ $EUID -ne 0 ]]; then
        log_message "INFO" "Requesting administrator privileges..."
        
        # Re-run script with sudo
        exec sudo "$0" "$@"
        exit $?
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
    ram_bytes=$(sysctl -n hw.memsize)
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
    local volumes_info
    volumes_info=$(diskutil list | grep -B3 "${CDROM_MARKER}" 2>/dev/null || true)
    
    if [[ -z "${volumes_info}" ]]; then
        # Try alternative detection method
        for volume in /Volumes/*; do
            if [[ -d "${volume}" ]]; then
                local volume_name
                volume_name=$(basename "${volume}")
                if [[ "${volume_name}" == *"${CDROM_MARKER}"* ]] || \
                   [[ -f "${volume}/.sunflower_system" ]]; then
                    CDROM_PATH="${volume}"
                    break
                fi
            fi
        done
    else
        # Extract mount point from diskutil output
        CDROM_PATH="/Volumes/$(diskutil info disk2s1 2>/dev/null | grep "Volume Name" | sed 's/.*: *//' || echo "")"
    fi
    
    if [[ -z "${CDROM_PATH}" ]] || [[ ! -d "${CDROM_PATH}" ]]; then
        log_message "ERROR" "CD-ROM partition with marker ${CDROM_MARKER} not found"
        return ${ERROR_CDROM_NOT_FOUND}
    fi
    
    # Verify expected structure
    if [[ ! -d "${CDROM_PATH}/system/models" ]]; then
        log_message "ERROR" "CD-ROM partition missing system directory structure"
        return ${ERROR_CDROM_NOT_FOUND}
    fi
    
    log_message "INFO" "CD-ROM partition found at ${CDROM_PATH}"
    return 0
}

detect_usb_partition() {
    local volumes_info
    volumes_info=$(diskutil list | grep -B3 "${USB_MARKER}" 2>/dev/null || true)
    
    if [[ -z "${volumes_info}" ]]; then
        # Try alternative detection method
        for volume in /Volumes/*; do
            if [[ -d "${volume}" ]]; then
                local volume_name
                volume_name=$(basename "${volume}")
                if [[ "${volume_name}" == *"${USB_MARKER}"* ]]; then
                    # Verify it's writable
                    if touch "${volume}/.write_test" 2>/dev/null; then
                        rm -f "${volume}/.write_test"
                        USB_PATH="${volume}"
                        break
                    fi
                fi
            fi
        done
    else
        # Extract mount point from diskutil output
        USB_PATH="/Volumes/$(diskutil info disk2s2 2>/dev/null | grep "Volume Name" | sed 's/.*: *//' || echo "")"
    fi
    
    if [[ -z "${USB_PATH}" ]] || [[ ! -d "${USB_PATH}" ]]; then
        log_message "ERROR" "USB writable partition with marker ${USB_MARKER} not found"
        return ${ERROR_USB_NOT_FOUND}
    fi
    
    # Create required directories if they don't exist
    mkdir -p "${USB_PATH}/profiles"
    mkdir -p "${USB_PATH}/conversations"
    mkdir -p "${USB_PATH}/logs"
    mkdir -p "${USB_PATH}/config"
    
    log_message "INFO" "USB partition found at ${USB_PATH}"
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
        "${CDROM_PATH}/system/models/Sunflower_AI_Kids.modelfile"
        "${CDROM_PATH}/system/models/Sunflower_AI_Educator.modelfile"
        "${CDROM_PATH}/system/ollama/ollama"
    )
    
    for file in "${critical_files[@]}"; do
        if [[ ! -f "${file}" ]]; then
            log_message "ERROR" "Critical file missing: ${file}"
            return ${ERROR_INTEGRITY_CHECK_FAILED}
        fi
    done
    
    # Verify checksums if available
    if command -v shasum >/dev/null 2>&1; then
        while IFS=' ' read -r checksum filepath; do
            if [[ -f "${CDROM_PATH}/${filepath}" ]]; then
                local actual_checksum
                actual_checksum=$(shasum -a 256 "${CDROM_PATH}/${filepath}" | cut -d' ' -f1)
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
    CPU_CORES=$(sysctl -n hw.ncpu)
    local cpu_brand
    cpu_brand=$(sysctl -n machdep.cpu.brand_string)
    
    # Check for Apple Silicon
    local is_apple_silicon=0
    if [[ "${cpu_brand}" == *"Apple"* ]]; then
        is_apple_silicon=1
        HAS_GPU=1  # Apple Silicon has integrated GPU
    else
        # Check for dedicated GPU on Intel Macs
        local gpu_info
        gpu_info=$(system_profiler SPDisplaysDataType 2>/dev/null | grep -E "Chipset Model|Vendor" || true)
        if echo "${gpu_info}" | grep -qE "AMD|NVIDIA|Radeon"; then
            HAS_GPU=1
        fi
    fi
    
    # Calculate performance score
    PERF_SCORE=$((SYSTEM_RAM_GB * 10))
    PERF_SCORE=$((PERF_SCORE + CPU_CORES * 5))
    
    if [[ ${HAS_GPU} -eq 1 ]]; then
        PERF_SCORE=$((PERF_SCORE + 30))
    fi
    
    # Apple Silicon bonus
    if [[ ${is_apple_silicon} -eq 1 ]]; then
        PERF_SCORE=$((PERF_SCORE + 20))
    fi
    
    log_message "INFO" "Hardware: RAM=${SYSTEM_RAM_GB}GB, Cores=${CPU_CORES}, GPU=${HAS_GPU}, AppleSilicon=${is_apple_silicon}, Score=${PERF_SCORE}"
    return 0
}

select_optimal_model() {
    # Model selection based on performance score
    # Score ranges: 0-50 (minimal), 51-80 (low), 81-120 (mid), 121+ (high)
    
    if [[ ${PERF_SCORE} -ge 121 ]]; then
        SELECTED_MODEL="llama3.2:7b"
        MODEL_TIER="high"
    elif [[ ${PERF_SCORE} -ge 81 ]]; then
        SELECTED_MODEL="llama3.2:3b"
        MODEL_TIER="mid"
    elif [[ ${PERF_SCORE} -ge 51 ]]; then
        SELECTED_MODEL="llama3.2:1b"
        MODEL_TIER="low"
    else
        SELECTED_MODEL="llama3.2:1b-q4_0"
        MODEL_TIER="minimal"
    fi
    
    log_message "INFO" "Selected model: ${SELECTED_MODEL} (tier: ${MODEL_TIER})"
    
    # Write configuration
    cat > "${USB_PATH}/config/hardware.json" <<EOF
{
    "selected_model": "${SELECTED_MODEL}",
    "performance_score": ${PERF_SCORE},
    "tier": "${MODEL_TIER}",
    "platform": "macos",
    "cpu_cores": ${CPU_CORES},
    "ram_gb": ${SYSTEM_RAM_GB},
    "has_gpu": ${HAS_GPU}
}
EOF
    
    return 0
}

# ==================== PYTHON ENVIRONMENT ====================
setup_python_environment() {
    # Check for embedded Python first
    if [[ -f "${CDROM_PATH}/system/python/bin/python3" ]]; then
        PYTHON_EXE="${CDROM_PATH}/system/python/bin/python3"
        log_message "INFO" "Using embedded Python"
    else
        # Check for system Python 3
        if command -v python3 >/dev/null 2>&1; then
            PYTHON_EXE="python3"
            log_message "INFO" "Using system Python 3"
        elif command -v python >/dev/null 2>&1; then
            # Check if python points to Python 3
            local python_version
            python_version=$(python --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
            if [[ "${python_version%%.*}" -ge 3 ]]; then
                PYTHON_EXE="python"
                log_message "INFO" "Using system Python"
            else
                log_message "ERROR" "Python 3 not found"
                return ${ERROR_PYTHON_NOT_FOUND}
            fi
        else
            log_message "ERROR" "Python not found in system or embedded location"
            return ${ERROR_PYTHON_NOT_FOUND}
        fi
    fi
    
    # Set Python environment variables
    export PYTHONPATH="${CDROM_PATH}/system:${CDROM_PATH}/system/lib"
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONUNBUFFERED=1
    
    return 0
}

# ==================== OLLAMA SETUP ====================
initialize_ollama() {
    local ollama_exe="${CDROM_PATH}/system/ollama/ollama"
    local ollama_models="${CDROM_PATH}/system/models"
    local ollama_home="${USB_PATH}/ollama_data"
    
    # Make Ollama executable
    chmod +x "${ollama_exe}"
    
    # Create Ollama data directory
    mkdir -p "${ollama_home}"
    
    # Set Ollama environment
    export OLLAMA_HOME="${ollama_home}"
    export OLLAMA_MODELS="${ollama_models}"
    
    # Start Ollama service
    log_message "INFO" "Starting Ollama service..."
    "${ollama_exe}" serve > "${USB_PATH}/logs/ollama.log" 2>&1 &
    local ollama_pid=$!
    
    # Store PID for cleanup
    echo ${ollama_pid} > "${USB_PATH}/ollama.pid"
    
    # Wait for Ollama to be ready
    local max_attempts=30
    local attempt=0
    while [[ ${attempt} -lt ${max_attempts} ]]; do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            break
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    
    if [[ ${attempt} -eq ${max_attempts} ]]; then
        log_message "ERROR" "Ollama service failed to start"
        return 1
    fi
    
    # Load the selected model
    log_message "INFO" "Loading AI model: ${SELECTED_MODEL}"
    "${ollama_exe}" pull "${ollama_models}/${SELECTED_MODEL}.bin" 2>&1 | tee -a "${USB_PATH}/logs/ollama.log"
    
    return 0
}

# ==================== APPLICATION LAUNCH ====================
launch_application() {
    # Set all required environment variables
    export SUNFLOWER_CDROM_PATH="${CDROM_PATH}"
    export SUNFLOWER_USB_PATH="${USB_PATH}"
    export SUNFLOWER_MODEL="${SELECTED_MODEL}"
    export SUNFLOWER_LOG_DIR="${USB_PATH}/logs"
    
    log_message "INFO" "Launching Sunflower AI application"
    
    # Create LaunchAgent for auto-restart capability
    create_launch_agent
    
    # Launch the main application
    "${PYTHON_EXE}" "${CDROM_PATH}/system/launcher_common.py" \
        --cdrom "${CDROM_PATH}" \
        --usb "${USB_PATH}" \
        --model "${SELECTED_MODEL}" \
        --platform "macos" \
        --log-file "${USB_PATH}/logs/app_$(date +%Y%m%d).log"
    
    local exit_code=$?
    if [[ ${exit_code} -ne 0 ]]; then
        log_message "ERROR" "Application exited with error code ${exit_code}"
        show_user_error "Application Error" "The application encountered an error. Please check the logs."
    fi
    
    return ${exit_code}
}

# ==================== LAUNCH AGENT ====================
create_launch_agent() {
    local launch_agent_dir="${HOME}/Library/LaunchAgents"
    local launch_agent_plist="${launch_agent_dir}/com.sunflowerai.education.plist"
    
    mkdir -p "${launch_agent_dir}"
    
    cat > "${launch_agent_plist}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.sunflowerai.education</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_EXE}</string>
        <string>${CDROM_PATH}/system/launcher_common.py</string>
        <string>--cdrom</string>
        <string>${CDROM_PATH}</string>
        <string>--usb</string>
        <string>${USB_PATH}</string>
        <string>--model</string>
        <string>${SELECTED_MODEL}</string>
        <string>--platform</string>
        <string>macos</string>
    </array>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>${USB_PATH}/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${USB_PATH}/logs/stderr.log</string>
</dict>
</plist>
EOF
    
    # Load the launch agent (but don't start it)
    launchctl load -w "${launch_agent_plist}" 2>/dev/null || true
    
    log_message "INFO" "LaunchAgent created for future sessions"
}

# ==================== CLEANUP ====================
cleanup() {
    log_message "INFO" "Performing cleanup..."
    
    # Stop Ollama service gracefully
    if [[ -f "${USB_PATH}/ollama.pid" ]]; then
        local ollama_pid
        ollama_pid=$(cat "${USB_PATH}/ollama.pid")
        if kill -0 ${ollama_pid} 2>/dev/null; then
            kill -TERM ${ollama_pid}
            sleep 2
            kill -0 ${ollama_pid} 2>/dev/null && kill -KILL ${ollama_pid}
        fi
        rm -f "${USB_PATH}/ollama.pid"
    fi
    
    log_message "INFO" "Launcher shutdown complete"
}

# ==================== SIGNAL HANDLERS ====================
trap cleanup EXIT
trap 'echo "Interrupted"; cleanup; exit 130' INT TERM

# ==================== MAIN EXECUTION ====================
main() {
    initialize
    
    echo -e "${CYAN}[1/7]${NC} Checking system requirements..."
    check_admin_privileges
    validate_macos_version || exit $?
    validate_system_ram || exit $?
    
    echo -e "${CYAN}[2/7]${NC} Detecting Sunflower AI device..."
    detect_cdrom_partition || {
        show_user_error "CD-ROM Partition Not Found" "Please ensure the Sunflower AI device is properly connected"
        exit ${ERROR_CDROM_NOT_FOUND}
    }
    
    detect_usb_partition || {
        show_user_error "USB Partition Not Found" "The writable partition could not be detected"
        exit ${ERROR_USB_NOT_FOUND}
    }
    
    echo -e "${CYAN}[3/7]${NC} Verifying system integrity..."
    verify_system_integrity || {
        show_user_error "Integrity Check Failed" "System files may be corrupted."
        exit ${ERROR_INTEGRITY_CHECK_FAILED}
    }
    
    echo -e "${CYAN}[4/7]${NC} Analyzing hardware capabilities..."
    detect_hardware_capabilities
    select_optimal_model
    
    echo -e "${CYAN}[5/7]${NC} Setting up Python environment..."
    setup_python_environment || {
        show_user_error "Python Setup Failed" "Unable to initialize Python environment"
        exit ${ERROR_PYTHON_NOT_FOUND}
    }
    
    echo -e "${CYAN}[6/7]${NC} Initializing AI models..."
    initialize_ollama || {
        show_user_error "AI Model Setup Failed" "Unable to initialize AI models"
        exit 1
    }
    
    echo -e "${CYAN}[7/7]${NC} Starting Sunflower AI..."
    echo ""
    launch_application
}

# Run main function
main "$@"
