#!/bin/bash

# Source common functions if not already sourced
if [ -z "$COMMON_SOURCED" ]; then
    source "$(dirname "$0")/common.sh"
fi

install_ffvship() {
    if ! command -v FFVship &> /dev/null; then
        log_info "Compiling FFVship..."
        
        mkdir -p build_tmp
        cd build_tmp || exit 1

        if [ -d "Vship" ]; then rm -rf Vship; fi
        git clone https://codeberg.org/Line-fr/Vship.git || { log_error "Failed to clone Vship"; cd ..; return 1; }
        cd Vship || { log_error "Failed to cd into Vship"; cd ..; cd ..; return 1; }
        
        if command -v nvcc &> /dev/null; then
            make buildcuda || { log_error "FFVship buildcuda failed"; cd ..; cd ..; return 1; }
        elif command -v hipcc &> /dev/null; then
            make build || { log_error "FFVship build failed"; cd ..; cd ..; return 1; }
        else
            log_warn "Neither nvcc nor hipcc found. Attempting Vulkan build."
            make buildVulkan || { log_error "FFVship buildVulkan failed (no Vulkan SDK?)"; cd ..; cd ..; return 1; }
        fi

        make buildFFVSHIP || { log_error "FFVship make buildFFVSHIP failed"; cd ..; cd ..; return 1; }
        make install PREFIX=/usr/local || { log_error "FFVship make install failed"; cd ..; cd ..; return 1; }
        cd .. 
        cd .. # Exit build_tmp
        
        log_success "FFVship installed."
    else
        log_info "FFVship is already installed."
    fi
}

uninstall_ffvship() {
    log_info "Uninstalling FFVship..."
    rm -vf /usr/local/bin/FFVship
    log_success "FFVship uninstalled."
}
