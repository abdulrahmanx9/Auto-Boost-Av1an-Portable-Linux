#!/bin/bash

# Source common functions if not already sourced
if [ -z "$COMMON_SOURCED" ]; then
    source "$(dirname "$0")/common.sh"
fi

install_svt_av1() {
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

        mkdir -p build_tmp
        cd build_tmp || exit 1

        if [ -d "svt-av1-psy" ]; then rm -rf svt-av1-psy; fi
        git clone https://github.com/5fish/svt-av1-psy.git || { log_error "Failed to clone SVT-AV1-PSY"; cd ..; return 1; }
        cd svt-av1-psy || { log_error "Failed to cd into svt-av1-psy"; cd ..; cd ..; return 1; }
        git checkout 2f788d04 || log_warn "Commit 2f788d04 not found. Using latest main."
        
        mkdir -p Build/linux
        cd Build/linux || { log_error "Failed to cd into Build/linux"; cd ..; cd ..; cd ..; return 1; }
        
        cmake ../.. -G"Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
            -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
            -DSVT_AV1_PGO=ON -DSVT_AV1_LTO=ON || { log_error "SVT-AV1 cmake failed"; cd ..; cd ..; cd ..; return 1; }
        
        make -j "$(nproc)" || { log_error "SVT-AV1 make failed"; cd ..; cd ..; cd ..; return 1; }
        make install || { log_error "SVT-AV1 make install failed"; cd ..; cd ..; cd ..; return 1; }
        cd ../../..
        cd .. # Exit build_tmp
        
        log_success "SVT-AV1-PSY installed."
    else
        log_info "SvtAv1EncApp is already installed."
    fi
}

uninstall_svt_av1() {
    log_info "Uninstalling SVT-AV1-PSY..."
    rm -vf /usr/local/bin/SvtAv1EncApp
    rm -vf /usr/local/lib/libSvtAv1Enc*
    rm -rf /usr/local/include/svt-av1
    rm -vf /usr/local/lib/pkgconfig/SvtAv1Enc.pc
    log_success "SVT-AV1-PSY uninstalled."
}
