#!/bin/bash

# Source common functions if not already sourced
if [ -z "$COMMON_SOURCED" ]; then
    source "$(dirname "$0")/common.sh"
fi

install_fssimu2() {
    if ! command -v fssimu2 &> /dev/null; then
        log_info "Installing fssimu2 (Zig Build)..."
        
        local ZIG_VERSION="0.15.1"
        local ZIG_TARBALL="zig-x86_64-linux-${ZIG_VERSION}.tar.xz"
        local ZIG_URL="https://ziglang.org/download/${ZIG_VERSION}/${ZIG_TARBALL}"
        local ZIG_DIR="zig-x86_64-linux-${ZIG_VERSION}"
        
        if [ ! -f "/usr/local/bin/zig" ] || ! zig version 2>/dev/null | grep -q "${ZIG_VERSION}"; then
            log_info "Downloading Zig ${ZIG_VERSION}..."
            wget -q "$ZIG_URL" -O "/tmp/${ZIG_TARBALL}" || { log_error "Failed to download Zig"; return 1; }
            tar -xf "/tmp/${ZIG_TARBALL}" -C /tmp || { log_error "Failed to extract Zig"; return 1; }
            cp "/tmp/${ZIG_DIR}/zig" /usr/local/bin/ || { log_error "Failed to copy Zig binary"; return 1; }
            cp -r "/tmp/${ZIG_DIR}/lib" /usr/local/lib/zig || { log_error "Failed to copy Zig lib"; return 1; }
            rm -rf "/tmp/${ZIG_TARBALL}" "/tmp/${ZIG_DIR}"
        fi
        
        mkdir -p build_tmp
        cd build_tmp || exit 1
        
        if [ -d "fssimu2" ]; then rm -rf fssimu2; fi
        git clone https://github.com/gianni-rosato/fssimu2.git || { log_error "Failed to clone fssimu2"; cd ..; return 1; }
        cd fssimu2 || { log_error "Failed to cd into fssimu2"; cd ..; cd ..; return 1; }
        
        log_info "Building fssimu2..."
        zig build --release=fast --prefix /usr/local || { log_error "fssimu2 build failed"; cd ..; cd ..; return 1; }
        
        cd ../.. 
        
        if command -v fssimu2 &> /dev/null; then
            log_success "fssimu2 installed."
        else
            log_warn "fssimu2 build may have failed."
        fi
    else
        log_info "fssimu2 is already installed."
    fi
}

uninstall_fssimu2() {
    log_info "Uninstalling fssimu2..."
    rm -vf /usr/local/bin/fssimu2
    rm -vf /usr/local/lib/libssimu2*
    rm -rf /usr/local/include/ssimu2.h
    log_success "fssimu2 uninstalled."
}
