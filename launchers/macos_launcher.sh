#!/bin/bash
# Sunflower AI Professional System - macOS Launcher
# Version: 6.2.0
# Production-ready launcher for macOS systems

set -euo pipefail  # Exit on error, undefined variables, pipe failures

# ==================== CONFIGURATION ====================
readonly VERSION="6.2.0"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="${HOME}/Library/Logs/sunflower_launcher_$(date +%Y%m%d).log"
readonly MIN_MACOS_VERSION="11.0"
readonly MIN_RAM_GB=4
readonly CDROM_MARKER="SUNFLOWER_CD"
readonly USB_MARKER="SUNFLOWER_DATA"

# Error codes
readonly ERROR_NO_ADMIN=1
readonly ERROR_INCOMPATIBLE_OS=2
readonly ERROR_INSUFFICIENT_RAM=3
readonly ERROR_CDROM_NOT_FOUND=4
readonly ERROR_USB_NOT_FOUND=5
readonly ERROR_INTEGRITY_CHECK_FAILED=6
readonly ERROR_PYTHON_NOT_FOUND=7
readonly ERROR_OLLAMA_FAILED=8

# Global variables
CDROM_PATH=""
USB_PATH=""
PYTHON_PATH=""
HARDWARE_TIER=""

# ==================== LOGGING FUNCTIONS ====================
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "[${timestamp}] [${level}] ${message}" >> "${LOG_FILE}"
    
    case "${level}" in
        ERROR)
            echo "❌ ${message}" >&2
            ;;
        WARNING)
            echo "⚠️  ${message}"
            ;;
        INFO)
            echo "ℹ️  ${message}"
            ;;
        SUCCESS)
            echo "✅ ${message}"
            ;;
    esac
}

# ==================== SYSTEM CHECKS ====================
check_admin_privileges() {
    if [[ "${EUID}" -eq 0 ]]; then
        return 0
    fi
    
    # Check if user can sudo without password for this script
    if sudo -n true 2>/dev/null; then
        return 0
    fi
    
    log_message "WARNING" "Admin privileges may be required for some operations"
    return 0  # Continue anyway, prompt for password if needed
}

validate_macos_version() {
    local current_version
    current_version=$(sw_vers -productVersion)
    
    # Compare versions
    if [[ "$(printf '%s\n' "${MIN_MACOS_VERSION}" "${current_version}" | sort -V | head -n1)" != "${MIN_MACOS_VERSION}" ]]; then
        log_message "ERROR" "macOS ${current_version} is below minimum required version ${MIN_MACOS_VERSION}"
        return ${ERROR_INCOMPATIBLE_OS}
    fi
    
    log_message "INFO" "macOS version ${current_version} meets requirements"
    return 0
}

validate_system_ram() {
    local system_ram_bytes
    system_ram_bytes=$(sysctl -n hw.memsize)
    local system_ram_gb=$((system_ram_bytes / 1073741824))
    
    if [[ ${system_ram_gb} -lt ${MIN_RAM_GB} ]]; then
        log_message "ERROR" "System RAM: ${system_ram_gb}GB. Minimum required: ${MIN_RAM_GB}GB"
        return ${ERROR_INSUFFICIENT_RAM}
    fi
    
    log_message "INFO" "System RAM: ${system_ram_gb}GB - meets requirements"
    return 0
}

# ==================== PARTITION DETECTION ====================
detect_cdrom_partition() {
    local volumes_info
    local volume_name
    local disk_device
    
    # First, try to find disk by label
    volumes_info=$(diskutil list | grep -B3 "${CDROM_MARKER}" 2>/dev/null || true)
    
    if [[ -n "${volumes_info}" ]]; then
        # Extract disk identifier (e.g., disk2s1)
        disk_device=$(echo "${volumes_info}" | grep -o 'disk[0-9]*s[0-9]*' | head -1)
        
        if [[ -n "${disk_device}" ]]; then
            # FIX: Properly validate diskutil output before using it
            volume_name=$(diskutil info "${disk_device}" 2>/dev/null | grep "Volume Name:" | sed 's/.*Volume Name: *//' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
            
            if [[ -n "${volume_name}" ]]; then
                CDROM_PATH="/Volumes/${volume_name}"
                
                # Verify the path actually exists
                if [[ -d "${CDROM_PATH}" ]]; then
                    log_message "INFO" "CD-ROM partition found at ${CDROM_PATH}"
                    return 0
                else
                    log_message "WARNING" "Volume name found but path doesn't exist: ${CDROM_PATH}"
                fi
            else
                log_message "WARNING" "Failed to get volume name from disk ${disk_device}"
            fi
        fi
    fi
    
    # Fallback: Try alternative detection method by checking mounted volumes
    for volume in /Volumes/*; do
        if [[ -d "${volume}" ]]; then
            local volume_name
            volume_name=$(basename "${volume}")
            
            # Check for marker file or name pattern
            if [[ "${volume_name}" == *"${CDROM_MARKER}"* ]] || \
               [[ -f "${volume}/.sunflower_system" ]] || \
               [[ -f "${volume}/sunflower_cd.id" ]]; then
                CDROM_PATH="${volume}"
                
                # Verify expected structure
                if [[ -d "${CDROM_PATH}/system" ]] || [[ -d "${CDROM_PATH}/models" ]]; then
                    log_message "INFO" "CD-ROM partition found at ${CDROM_PATH} (fallback method)"
                    return 0
                fi
            fi
        fi
    done
    
    log_message "ERROR" "CD-ROM partition with marker ${CDROM_MARKER} not found"
    return ${ERROR_CDROM_NOT_FOUND}
}

detect_usb_partition() {
    local volumes_info
    local volume_name
    local disk_device
    
    # First, try to find disk by label
    volumes_info=$(diskutil list | grep -B3 "${USB_MARKER}" 2>/dev/null || true)
    
    if [[ -n "${volumes_info}" ]]; then
        # Extract disk identifier (e.g., disk2s2)
        disk_device=$(echo "${volumes_info}" | grep -o 'disk[0-9]*s[0-9]*' | head -1)
        
        if [[ -n "${disk_device}" ]]; then
            # FIX: Properly validate diskutil output before using it
            volume_name=$(diskutil info "${disk_device}" 2>/dev/null | grep "Volume Name:" | sed 's/.*Volume Name: *//' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
            
            if [[ -n "${volume_name}" ]]; then
                USB_PATH="/Volumes/${volume_name}"
                
                # Verify the path actually exists and is writable
                if [[ -d "${USB_PATH}" ]]; then
                    # Test write permission
                    if touch "${USB_PATH}/.write_test" 2>/dev/null; then
                        rm -f "${USB_PATH}/.write_test"
                        log_message "INFO" "USB partition found at ${USB_PATH}"
                        return 0
                    else
                        log_message "WARNING" "USB partition found but not writable: ${USB_PATH}"
                    fi
                else
                    log_message "WARNING" "Volume name found but path doesn't exist: ${USB_PATH}"
                fi
            else
                log_message "WARNING" "Failed to get volume name from disk ${disk_device}"
            fi
        fi
    fi
    
    # Fallback: Try alternative detection method by checking mounted volumes
    for volume in /Volumes/*; do
        if [[ -d "${volume}" ]]; then
            local volume_name
            volume_name=$(basename "${volume}")
            
            # Check for marker file or name pattern
            if [[ "${volume_name}" == *"${USB_MARKER}"* ]] || \
               [[ -f "${volume}/sunflower_data.id" ]]; then
                # Verify it's writable
                if touch "${volume}/.write_test" 2>/dev/null; then
                    rm -f "${volume}/.write_test"
                    USB_PATH="${volume}"
                    log_message "INFO" "USB partition found at ${USB_PATH} (fallback method)"
                    return 0
                fi
            fi
        fi
    done
    
    log_message "ERROR" "USB partition with marker ${USB_MARKER} not found"
    return ${ERROR_USB_NOT_FOUND}
}

# ==================== INTEGRITY CHECK ====================
verify_system_integrity() {
    log_message "INFO" "Verifying system integrity..."
    
    # Check for required system files on CD-ROM partition
    local required_files=(
        "${CDROM_PATH}/system/checksums.sha256"
        "${CDROM_PATH}/system/manifest.json"
        "${CDROM_PATH}/models"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -e "${file}" ]]; then
            log_message "ERROR" "Required file missing: ${file}"
            return ${ERROR_INTEGRITY_CHECK_FAILED}
        fi
    done
    
    # Verify checksums if available
    if [[ -f "${CDROM_PATH}/system/checksums.sha256" ]]; then
        log_message "INFO" "Verifying file checksums..."
        
        pushd "${CDROM_PATH}" > /dev/null
        if shasum -a 256 -c "system/checksums.sha256" --quiet 2>/dev/null; then
            log_message "SUCCESS" "Checksum verification passed"
        else
            log_message "WARNING" "Some checksums did not match"
            # Don't fail, just warn
        fi
        popd > /dev/null
    fi
    
    return 0
}

# ==================== PYTHON SETUP ====================
setup_python_environment() {
    log_message "INFO" "Setting up Python environment..."
    
    # Check for Python 3.11+
    for python_cmd in python3.11 python3.12 python3; do
        if command -v ${python_cmd} &> /dev/null; then
            local python_version
            python_version=$(${python_cmd} --version 2>&1 | cut -d' ' -f2)
            local major_minor
            major_minor=$(echo "${python_version}" | cut -d. -f1,2)
            
            if [[ "$(echo "${major_minor} >= 3.11" | bc)" -eq 1 ]]; then
                PYTHON_PATH=$(command -v ${python_cmd})
                log_message "SUCCESS" "Found Python ${python_version} at ${PYTHON_PATH}"
                return 0
            fi
        fi
    done
    
    log_message "ERROR" "Python 3.11+ not found"
    return ${ERROR_PYTHON_NOT_FOUND}
}

create_virtual_environment() {
    local venv_path="${USB_PATH}/sunflower_venv"
    
    if [[ ! -d "${venv_path}" ]]; then
        log_message "INFO" "Creating virtual environment..."
        "${PYTHON_PATH}" -m venv "${venv_path}"
    fi
    
    # Activate virtual environment
    source "${venv_path}/bin/activate"
    
    # Install required packages
    if [[ -f "${CDROM_PATH}/system/requirements.txt" ]]; then
        log_message "INFO" "Installing Python dependencies..."
        pip install --quiet --upgrade pip
        pip install --quiet -r "${CDROM_PATH}/system/requirements.txt"
    fi
    
    return 0
}

# ==================== OLLAMA SETUP ====================
setup_ollama() {
    log_message "INFO" "Setting up Ollama..."
    
    # Check if Ollama is already installed
    if command -v ollama &> /dev/null; then
        log_message "INFO" "Ollama already installed"
    else
        # Install Ollama from CD-ROM
        if [[ -f "${CDROM_PATH}/system/ollama/install.sh" ]]; then
            log_message "INFO" "Installing Ollama from device..."
            bash "${CDROM_PATH}/system/ollama/install.sh"
        else
            log_message "ERROR" "Ollama installer not found"
            return ${ERROR_OLLAMA_FAILED}
        fi
    fi
    
    # Start Ollama service
    log_message "INFO" "Starting Ollama service..."
    ollama serve > "${USB_PATH}/logs/ollama.log" 2>&1 &
    local ollama_pid=$!
    
    # Wait for Ollama to be ready
    local max_attempts=30
    local attempt=0
    
    while [[ ${attempt} -lt ${max_attempts} ]]; do
        if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
            log_message "SUCCESS" "Ollama service started (PID: ${ollama_pid})"
            echo ${ollama_pid} > "${USB_PATH}/ollama.pid"
            return 0
        fi
        
        sleep 1
        ((attempt++))
    done
    
    log_message "ERROR" "Ollama service failed to start"
    return ${ERROR_OLLAMA_FAILED}
}

# ==================== MODEL LOADING ====================
detect_hardware_tier() {
    local ram_gb=$(($(sysctl -n hw.memsize) / 1073741824))
    local cpu_cores=$(sysctl -n hw.ncpu)
    
    if [[ ${ram_gb} -ge 16 ]] && [[ ${cpu_cores} -ge 8 ]]; then
        HARDWARE_TIER="high"
    elif [[ ${ram_gb} -ge 8 ]] && [[ ${cpu_cores} -ge 4 ]]; then
        HARDWARE_TIER="medium"
    elif [[ ${ram_gb} -ge 4 ]]; then
        HARDWARE_TIER="low"
    else
        HARDWARE_TIER="minimum"
    fi
    
    log_message "INFO" "Hardware tier detected: ${HARDWARE_TIER} (${ram_gb}GB RAM, ${cpu_cores} cores)"
}

load_appropriate_model() {
    detect_hardware_tier
    
    local model_name=""
    case "${HARDWARE_TIER}" in
        high)
            model_name="sunflower-kids-7b"
            ;;
        medium)
            model_name="sunflower-kids-3b"
            ;;
        low|minimum)
            model_name="sunflower-kids-1b"
            ;;
    esac
    
    log_message "INFO" "Loading model: ${model_name}"
    
    # Create model from modelfile
    if [[ -f "${CDROM_PATH}/modelfiles/Sunflower_AI_Kids.modelfile" ]]; then
        ollama create "${model_name}" -f "${CDROM_PATH}/modelfiles/Sunflower_AI_Kids.modelfile"
        
        # Load model into memory
        ollama run "${model_name}" "Initialize" > /dev/null 2>&1
        
        log_message "SUCCESS" "Model ${model_name} loaded successfully"
    else
        log_message "ERROR" "Modelfile not found"
        return 1
    fi
    
    return 0
}

# ==================== MAIN APPLICATION LAUNCH ====================
launch_sunflower_app() {
    log_message "INFO" "Launching Sunflower AI Professional System..."
    
    # Set environment variables
    export SUNFLOWER_CDROM_PATH="${CDROM_PATH}"
    export SUNFLOWER_USB_PATH="${USB_PATH}"
    export SUNFLOWER_HARDWARE_TIER="${HARDWARE_TIER}"
    export SUNFLOWER_PLATFORM="macos"
    
    # Launch the main application
    if [[ -f "${CDROM_PATH}/system/main.py" ]]; then
        cd "${USB_PATH}"
        "${PYTHON_PATH}" "${CDROM_PATH}/system/main.py" \
            --cdrom-path "${CDROM_PATH}" \
            --usb-path "${USB_PATH}" \
            --hardware-tier "${HARDWARE_TIER}" \
            --log-file "${USB_PATH}/logs/sunflower.log"
    else
        log_message "ERROR" "Main application not found"
        return 1
    fi
}

# ==================== CLEANUP ====================
cleanup() {
    log_message "INFO" "Performing cleanup..."
    
    # Stop Ollama if we started it
    if [[ -f "${USB_PATH}/ollama.pid" ]]; then
        local ollama_pid=$(cat "${USB_PATH}/ollama.pid")
        if kill -0 ${ollama_pid} 2>/dev/null; then
            kill ${ollama_pid}
            log_message "INFO" "Stopped Ollama service"
        fi
        rm -f "${USB_PATH}/ollama.pid"
    fi
    
    # Deactivate virtual environment
    if [[ -n "${VIRTUAL_ENV}" ]]; then
        deactivate
    fi
    
    log_message "INFO" "Cleanup completed"
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# ==================== MAIN EXECUTION ====================
main() {
    clear
    
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║              SUNFLOWER AI PROFESSIONAL SYSTEM v${VERSION}         ║"
    echo "║                   Family-Safe K-12 STEM Education                ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    
    log_message "INFO" "Launcher started - Version ${VERSION}"
    
    # System checks
    echo "🔍 [1/7] Checking system requirements..."
    check_admin_privileges
    validate_macos_version || exit $?
    validate_system_ram || exit $?
    
    # Partition detection
    echo "💾 [2/7] Detecting Sunflower AI device..."
    detect_cdrom_partition || exit $?
    detect_usb_partition || exit $?
    
    # Integrity check
    echo "🔐 [3/7] Verifying system integrity..."
    verify_system_integrity || exit $?
    
    # Python setup
    echo "🐍 [4/7] Setting up Python environment..."
    setup_python_environment || exit $?
    create_virtual_environment || exit $?
    
    # Ollama setup
    echo "🤖 [5/7] Setting up AI engine..."
    setup_ollama || exit $?
    
    # Model loading
    echo "📚 [6/7] Loading AI models..."
    load_appropriate_model || exit $?
    
    # Launch application
    echo "🚀 [7/7] Starting Sunflower AI..."
    launch_sunflower_app
    
    log_message "SUCCESS" "Sunflower AI Professional System launched successfully"
}

# Run main function
main "$@"
