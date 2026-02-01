#!/bin/bash

# Source common functions if not already sourced
if [ -z "$COMMON_SOURCED" ]; then
    source "$(dirname "$0")/common.sh"
fi

install_vszip() {
    local VS_PLUGIN_PATH=""
    if command -v pkg-config &> /dev/null; then
        VS_PLUGIN_PATH=$(pkg-config --variable=libdir vapoursynth)/vapoursynth
    else
        VS_PLUGIN_PATH="/usr/lib/x86_64-linux-gnu/vapoursynth"
    fi
    mkdir -p "$VS_PLUGIN_PATH"

    mkdir -p build_tmp
    cd build_tmp || exit 1
    
    log_info "Compiling VSZIP..."
    if [ -d "vszip" ]; then rm -rf vszip; fi
    git clone https://github.com/dnjulek/vapoursynth-zip.git vszip || { log_error "Failed to clone VSZIP"; cd ..; return 1; }
    cd vszip || { log_error "Failed to cd into vszip"; cd ..; cd ..; return 1; }
    
    cd build-help
    chmod +x build.sh
    ./build.sh || { log_error "VSZIP build.sh failed"; cd ..; cd ..; cd ..; return 1; }
    
    if [ -f "../zig-out/lib/libvszip.so" ]; then
        cp "../zig-out/lib/libvszip.so" "$VS_PLUGIN_PATH/libvszip.so" || { log_error "Failed to copy libvszip.so"; cd ..; cd ..; cd ..; return 1; }
        if [ -d "/usr/lib/x86_64-linux-gnu/vapoursynth" ]; then
            cp "../zig-out/lib/libvszip.so" "/usr/lib/x86_64-linux-gnu/vapoursynth/libvszip.so"
        fi
    else
        log_error "VSZIP Compilation failed!"
    fi
    cd ../..
    
    ldconfig
    cd .. # Exit build_tmp
    
    log_success "VSZIP installed."
}

uninstall_vszip() {
    log_info "Uninstalling VSZIP..."
    find /usr/local/lib/vapoursynth -name "libvszip.so" -delete
    find /usr/lib/x86_64-linux-gnu/vapoursynth -name "libvszip.so" -delete
    log_success "VSZIP uninstalled."
}
