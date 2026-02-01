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
        libavutil-dev libswscale-dev libavdevice-dev libavfilter-dev cython3 
        libzimg-dev python3-numpy python3-psutil python3-rich jq mediainfo 
        opus-tools x265 xclip meson ninja-build libass-dev nvidia-cuda-toolkit
        # Dependencies for fssimu2 (added here for convenience)
        libjpeg-turbo8-dev libwebp-dev libavif-dev
    )

    apt install -y "${DEPS[@]}" || { log_error "Failed to install system dependencies via apt"; return 1; }
    log_success "System packages installed."
}

uninstall_system_deps() {
    log_warn "Uninstalling system dependencies can break your system!"
    log_warn "This will remove packages like ffmpeg, python3, git, gcc, etc."
    if ask_yes_no "Are you ABSOLUTELY SURE you want to continue?" "N"; then
        local DEPS=(
            software-properties-common ffmpeg x264 mkvtoolnix mkvtoolnix-gui 
            python3 python3-pip git curl wget build-essential cmake pkg-config 
            autoconf automake libtool yasm nasm clang libavcodec-dev libavformat-dev 
            libavutil-dev libswscale-dev libavdevice-dev libavfilter-dev cython3 
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
