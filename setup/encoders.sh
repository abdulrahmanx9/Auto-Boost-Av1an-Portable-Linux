#!/bin/bash

# Source common functions if not already sourced
if [ -z "$COMMON_SOURCED" ]; then
    source "$(dirname "$0")/common.sh"
fi

install_encoders() {
    mkdir -p build_tmp
    cd build_tmp || exit 1

    # 1. SVT-AV1-PSY
    if ! command -v SvtAv1EncApp &> /dev/null; then
        log_info "Compiling SVT-AV1-PSY (5fish Fork)..."
        
        # Ensure llvm-profdata for PGO
        if ! command -v llvm-profdata &> /dev/null; then
            local LLVM_PROFDATA=$(find /usr/bin -name "llvm-profdata-*" | sort -V | tail -n 1)
            if [ -n "$LLVM_PROFDATA" ]; then
                log_info "Found $LLVM_PROFDATA. Linking..."
                ln -sf "$LLVM_PROFDATA" /usr/local/bin/llvm-profdata
                ln -sf "${LLVM_PROFDATA}" /usr/bin/llvm-profdata
            else
                log_warn "llvm-profdata not found. PGO might fail."
            fi
        fi

        if [ -d "svt-av1-psy" ]; then rm -rf svt-av1-psy; fi
        git clone https://github.com/5fish/svt-av1-psy.git
        cd svt-av1-psy
        git checkout 2f788d04 || log_warn "Commit 2f788d04 not found. Using latest main."
        
        mkdir -p Build/linux
        cd Build/linux
        
        cmake ../.. -G"Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
            -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
            -DSVT_AV1_PGO=ON -DSVT_AV1_LTO=ON
        
        make -j "$(nproc)"
        make install
        cd ../../.. # Back to build_tmp
        log_success "SVT-AV1-PSY installed."
    else
        log_info "SvtAv1EncApp is already installed."
    fi

    # 2. FFVship
    if ! command -v FFVship &> /dev/null; then
        log_info "Compiling FFVship..."
        
        if [ -d "Vship" ]; then rm -rf Vship; fi
        git clone https://github.com/Line-fr/Vship.git
        cd Vship
        
        if command -v nvcc &> /dev/null; then
            make buildcuda
        elif command -v hipcc &> /dev/null; then
            make build
        else
            log_warn "Neither nvcc nor hipcc found. Attempting CUDA build anyway."
            make buildcuda
        fi

        log_info "Building FFVship CLI..."
        make buildFFVSHIP
        make install PREFIX=/usr/local
        cd .. # Back to build_tmp
        log_success "FFVship installed."
    else
        log_info "FFVship is already installed."
    fi
    
    cd .. # Exit build_tmp
}
