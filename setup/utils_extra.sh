#!/bin/bash

# Source common functions if not already sourced
if [ -z "$COMMON_SOURCED" ]; then
    source "$(dirname "$0")/common.sh"
fi

install_utils_extra() {
    # 1. oxipng
    if ! command -v oxipng &> /dev/null; then
        log_info "Installing oxipng..."
        source "$HOME/.cargo/env"
        cargo install oxipng
        
        if [ -f "$HOME/.cargo/bin/oxipng" ]; then
            cp "$HOME/.cargo/bin/oxipng" /usr/local/bin/oxipng
            chmod +x /usr/local/bin/oxipng
            log_success "oxipng installed."
        fi
    else
        log_info "oxipng is already installed."
    fi

    # 2. fssimu2
    if ! command -v fssimu2 &> /dev/null; then
        log_info "Installing fssimu2 (Zig Build)..."
        
        local ZIG_VERSION="0.15.1"
        local ZIG_TARBALL="zig-x86_64-linux-${ZIG_VERSION}.tar.xz"
        local ZIG_URL="https://ziglang.org/download/${ZIG_VERSION}/${ZIG_TARBALL}"
        local ZIG_DIR="zig-x86_64-linux-${ZIG_VERSION}"
        
        if [ ! -f "/usr/local/bin/zig" ] || ! zig version 2>/dev/null | grep -q "${ZIG_VERSION}"; then
            log_info "Downloading Zig ${ZIG_VERSION}..."
            wget -q "$ZIG_URL" -O "/tmp/${ZIG_TARBALL}"
            tar -xf "/tmp/${ZIG_TARBALL}" -C /tmp
            cp "/tmp/${ZIG_DIR}/zig" /usr/local/bin/
            cp -r "/tmp/${ZIG_DIR}/lib" /usr/local/lib/zig
            rm -rf "/tmp/${ZIG_TARBALL}" "/tmp/${ZIG_DIR}"
        fi
        
        mkdir -p build_tmp
        cd build_tmp || exit 1
        
        if [ -d "fssimu2" ]; then rm -rf fssimu2; fi
        git clone https://github.com/gianni-rosato/fssimu2.git
        cd fssimu2
        
        log_info "Building fssimu2..."
        zig build --release=fast --prefix /usr/local
        
        cd ../.. # Back from build_tmp/fssimu2 -> setup root
        
        if command -v fssimu2 &> /dev/null; then
            log_success "fssimu2 installed."
        else
            log_warn "fssimu2 build may have failed."
        fi
    else
        log_info "fssimu2 is already installed."
    fi
}
