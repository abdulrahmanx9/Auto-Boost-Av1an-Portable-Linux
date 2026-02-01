#!/bin/bash

# Source common functions if not already sourced
if [ -z "$COMMON_SOURCED" ]; then
    source "$(dirname "$0")/common.sh"
fi

install_vs_plugins() {
    local VS_PLUGIN_PATH=""
    if command -v pkg-config &> /dev/null; then
        VS_PLUGIN_PATH=$(pkg-config --variable=libdir vapoursynth)/vapoursynth
    else
        VS_PLUGIN_PATH="/usr/lib/x86_64-linux-gnu/vapoursynth"
    fi
    mkdir -p "$VS_PLUGIN_PATH"

    mkdir -p build_tmp
    cd build_tmp || exit 1

    # 1. WWXD
    log_info "Compiling VapourSynth-WWXD..."
    if [ -d "vapoursynth-wwxd" ]; then rm -rf vapoursynth-wwxd; fi
    git clone https://github.com/dubhater/vapoursynth-wwxd.git
    cd vapoursynth-wwxd
    
    # Compile manually
    gcc -o libwwxd.so -fPIC -shared -O3 -Wall -Wextra -I. -I/usr/local/include/vapoursynth src/*.c -lm
    
    cp libwwxd.so "$VS_PLUGIN_PATH/"
    if [ -d "/usr/lib/x86_64-linux-gnu/vapoursynth" ]; then
        cp libwwxd.so "/usr/lib/x86_64-linux-gnu/vapoursynth/"
    fi
    cd ..
    
    # 2. VSZIP
    log_info "Compiling VSZIP..."
    if [ -d "vszip" ]; then rm -rf vszip; fi
    git clone https://github.com/dnjulek/vapoursynth-zip.git vszip
    cd vszip
    
    # Using existing build script that handles Zig
    cd build-help
    chmod +x build.sh
    ./build.sh
    
    if [ -f "../zig-out/lib/libvszip.so" ]; then
        cp "../zig-out/lib/libvszip.so" "$VS_PLUGIN_PATH/libvszip.so"
        if [ -d "/usr/lib/x86_64-linux-gnu/vapoursynth" ]; then
            cp "../zig-out/lib/libvszip.so" "/usr/lib/x86_64-linux-gnu/vapoursynth/libvszip.so"
        fi
    else
        log_error "VSZIP Compilation failed!"
    fi
    cd ../..
    
    ldconfig

    # 3. SubText
    log_info "Compiling SubText..."
    if [ -d "subtext" ]; then rm -rf subtext; fi
    git clone https://github.com/vapoursynth/subtext.git
    cd subtext
    mkdir build && cd build
    meson setup .. --buildtype=release
    ninja
    
    if [ -f "libsubtext.so" ]; then
        cp "libsubtext.so" "$VS_PLUGIN_PATH/"
    else
        log_error "SubText compilation failed!"
    fi
    
    cd ../../..
    
    log_success "VapourSynth plugins installed."
}
