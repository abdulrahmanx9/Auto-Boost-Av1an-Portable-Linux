#!/bin/bash

# Source common functions if not already sourced
if [ -z "$COMMON_SOURCED" ]; then
    source "$(dirname "$0")/common.sh"
fi

install_system_deps() {
    log_info "Updating apt..."
    apt update

    log_info "Installing System Packages..."
    # Core build tools and libraries
    local DEPS=(
        software-properties-common ffmpeg x264 mkvtoolnix mkvtoolnix-gui 
        python3 python3-pip git curl wget build-essential cmake pkg-config 
        autoconf automake libtool yasm nasm clang libavcodec-dev libavformat-dev 
        libavutil-dev libswscale-dev libavdevice-dev libavfilter-dev  
        libzimg-dev python3-numpy python3-psutil python3-rich jq mediainfo 
        opus-tools x265 xclip meson ninja-build libass-dev nvidia-cuda-toolkit
        # Dependencies for BestSource / fssimu2
        libjpeg-turbo8-dev libwebp-dev libavif-dev libxxhash-dev
    )

    apt install -y "${DEPS[@]}" || { log_error "Failed to install system dependencies via apt"; return 1; }
    
    log_info "Compiling FFmpeg master from source to satisfy BestSource (libavcodec >= 61.19.0)..."
    local CDIR="/tmp/ffmpeg_master_build"
    mkdir -p "$CDIR"
    cd "$CDIR"
    if [ -d "ffmpeg" ]; then rm -rf ffmpeg; fi
    git clone --depth 1 https://github.com/FFmpeg/FFmpeg.git ffmpeg || { log_error "Failed to clone ffmpeg repo"; return 1; }
    cd ffmpeg
    ./configure \
      --prefix="/usr/local" \
      --enable-shared \
      --enable-gpl \
      --enable-libx264 \
      --enable-libx265 \
      --enable-libass \
      --enable-libfreetype \
      --disable-doc \
      --disable-programs || { log_error "FFmpeg configure failed"; return 1; }
    make -j"$(nproc)" || { log_error "FFmpeg make failed"; return 1; }
    make install || { log_error "FFmpeg make install failed"; return 1; }
    ldconfig
    
    log_success "System packages and FFmpeg libraries installed."
}

uninstall_system_deps() {
    log_warn "Uninstalling system dependencies can break your system!"
    log_warn "This will remove packages like ffmpeg, python3, git, gcc, etc."
    if ask_yes_no "Are you ABSOLUTELY SURE you want to continue?" "N"; then
        local DEPS=(
            software-properties-common ffmpeg x264 mkvtoolnix mkvtoolnix-gui 
            python3 python3-pip git curl wget build-essential cmake pkg-config 
            autoconf automake libtool yasm nasm clang libavcodec-dev libavformat-dev 
            libavutil-dev libswscale-dev libavdevice-dev libavfilter-dev  
            libzimg-dev python3-numpy python3-psutil python3-rich jq mediainfo 
            opus-tools x265 xclip meson ninja-build libass-dev nvidia-cuda-toolkit
            libjpeg-turbo8-dev libwebp-dev libavif-dev
        )
        apt remove -y "${DEPS[@]}"
        log_success "System packages removed (hopefully you knew what you were doing)."
    else
        log_info "Uninstall aborted."
    fi
}
