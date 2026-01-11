#!/bin/bash
set -e

echo "=========================================================="
echo "   Auto-Boost-Av1an Dependency Installer for Ubuntu"
echo "=========================================================="
echo "Supported Distros: Debian/Ubuntu"
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo ./install_deps_linux.sh)"
    exit 1
fi

# Detect Distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    DISTRO_LIKE=$ID_LIKE
else
    echo "Cannot detect Linux distribution. Assuming generic/manual install required."
    exit 1
fi

echo "Detected Distribution: $DISTRO"

# Check for Ubuntu/Debian
if [ -f /etc/debian_version ]; then
    echo "Detected Debian/Ubuntu-based system."
else
    echo "Error: This script is officially supported only on Ubuntu/Debian."
    echo "Detected: $DISTRO"
    echo "If you are using Arch or Fedora, please install dependencies manually."
    exit 1
fi

echo "Updating apt..."
apt update
echo "Installing System Packages..."
# Added build deps for VapourSynth (cython3, libzimg-dev) and python libs
apt install -y software-properties-common ffmpeg x264 mkvtoolnix mkvtoolnix-gui python3 python3-pip git curl wget build-essential cmake pkg-config autoconf automake libtool yasm nasm clang libavcodec-dev libavformat-dev libavutil-dev libswscale-dev libavdevice-dev libavfilter-dev cython3 libzimg-dev python3-numpy python3-psutil python3-rich jq mediainfo opus-tools

# 3. Python Libraries (Install FIRST to allow source VS build to overwrite pip version)
echo "Installing Python Libraries..."
# Use --ignore-installed to avoid conflicts with apt-installed packages
pip3 install vsjetpack numpy rich vstools psutil --break-system-packages --ignore-installed

# Remove the pip-installed vapoursynth which conflicts with the source build we are about to do
echo "Removing pip-installed VapourSynth to avoid version mismatch..."
pip3 uninstall -y vapoursynth --break-system-packages || true

# VapourSynth (Build from Source since PPA is flaky on 24.04)
if ! command -v vspipe &> /dev/null; then
    echo "=========================================================="
    echo "Compiling VapourSynth from Source..."
    echo "=========================================================="
    mkdir -p build_tmp
    cd build_tmp
    
    # 1. ZIMG (Ensure latest)
    # Ubuntu 24.04 has libzimg-dev but let's assume it works.
    
    # 2. VapourSynth
    if [ -d "vapoursynth" ]; then rm -rf vapoursynth; fi
    git clone https://github.com/vapoursynth/vapoursynth.git
    cd vapoursynth
    ./autogen.sh
    ./configure
    make -j $(nproc)
    make install
    cd ..
    
    # Link Python module if not found
    # Ubuntu/Debian uses 'dist-packages' but VS installs to 'site-packages'
    SITE_PKG_DIR="/usr/local/lib/python3.12/site-packages"
    DIST_PKG_DIR="/usr/lib/python3/dist-packages"
    
    if [ -f "$SITE_PKG_DIR/vapoursynth.so" ]; then
        echo "Linking VapourSynth Python module to dist-packages..."
        ln -sf "$SITE_PKG_DIR/vapoursynth.so" "$DIST_PKG_DIR/vapoursynth.so"
    else
        echo "Warning: vapoursynth.so not found in $SITE_PKG_DIR"
    fi
    
    # 3. FFMS2
    echo "Compiling FFMS2..."
    if [ -d "ffms2" ]; then rm -rf ffms2; fi
    # Use tag 5.0 which is compatible with FFmpeg 6.x (Ubuntu 24.04). Master requires FFmpeg 7+.
    git clone --branch 5.0 https://github.com/FFMS/ffms2.git
    cd ffms2
    ./autogen.sh
    ./configure --enable-shared
    make -j $(nproc)
    make install
    cd ..
    
    # Symlink FFMS2 to VapourSynth Autoload Plugin Path
    # Determine VS plugin path
    VS_PLUGIN_PATH="/usr/local/lib/vapoursynth"
    mkdir -p "$VS_PLUGIN_PATH"
    
    if [ -f "/usr/local/lib/libffms2.so" ]; then
        echo "Linking FFMS2 to VapourSynth plugin folder..."
        ln -sf "/usr/local/lib/libffms2.so" "$VS_PLUGIN_PATH/libffms2.so"
    fi

    ldconfig
    cd ..
else
    echo "VapourSynth is already installed."
fi

# 4. Rust (for Av1an)
if ! command -v rustc &> /dev/null; then
    echo "Installing Rust..."
    if command -v pacman &> /dev/null; then
        pacman -S --noconfirm rust
    else
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source "$HOME/.cargo/env"
        export PATH="$HOME/.cargo/bin:$PATH"
    fi
else
    echo "Rust is already installed."
    # Ensure environment is loaded for subsequent steps if Rust was already installed
    source "$HOME/.cargo/env"
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# 5. Av1an
if ! command -v av1an &> /dev/null; then
    echo "Installing Av1an via Cargo (Git Source)..."
    # Configure environment
    source "$HOME/.cargo/env"
    
    # Ensure VapourSynth libraries (installed in /usr/local/lib) are found
    export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
    export LD_LIBRARY_PATH="/usr/local/lib:$LD_LIBRARY_PATH"
    export LIBRARY_PATH="/usr/local/lib:$LIBRARY_PATH"

    # Install Av1an from git to get latest features
    cargo install --git https://github.com/rust-av/Av1an.git --bin av1an 
    
    # Explicitly copy to /usr/local/bin to avoid root permission issues with ~/.cargo/bin
    if [ -f "$HOME/.cargo/bin/av1an" ]; then
        cp "$HOME/.cargo/bin/av1an" /usr/local/bin/av1an
        chmod +x /usr/local/bin/av1an
        echo "Av1an installed to /usr/local/bin/av1an"
    fi
else
    echo "Av1an is already installed."
    # Ensure environment is loaded for subsequent steps
    source "$HOME/.cargo/env"
    
    # Ensure update even if installed (in case of failed copy previously)
    if [ -f "$HOME/.cargo/bin/av1an" ] && [ ! -f "/usr/local/bin/av1an" ]; then
         cp "$HOME/.cargo/bin/av1an" /usr/local/bin/av1an
         chmod +x /usr/local/bin/av1an
    fi
    
    export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
    export LD_LIBRARY_PATH="/usr/local/lib:$LD_LIBRARY_PATH"
    export LIBRARY_PATH="/usr/local/lib:$LIBRARY_PATH"
fi

# 5b. fssimu2 (Standalone SSIMULACRA2 Metric Tool - Zig Build)
if ! command -v fssimu2 &> /dev/null; then
    echo "==========================================================="
    echo "Installing fssimu2 (Zig Build)..."
    echo "==========================================================="
    
    # Install fssimu2 dependencies
    apt install -y libjpeg-turbo8-dev libwebp-dev libavif-dev
    
    # Download Zig 0.15.1 (required version)
    ZIG_VERSION="0.15.1"
    ZIG_TARBALL="zig-x86_64-linux-${ZIG_VERSION}.tar.xz"
    ZIG_URL="https://ziglang.org/download/${ZIG_VERSION}/${ZIG_TARBALL}"
    ZIG_DIR="zig-x86_64-linux-${ZIG_VERSION}"
    
    if [ ! -f "/usr/local/bin/zig" ] || ! zig version 2>/dev/null | grep -q "${ZIG_VERSION}"; then
        echo "Downloading Zig ${ZIG_VERSION}..."
        wget -q "$ZIG_URL" -O "/tmp/${ZIG_TARBALL}"
        tar -xf "/tmp/${ZIG_TARBALL}" -C /tmp
        cp "/tmp/${ZIG_DIR}/zig" /usr/local/bin/
        cp -r "/tmp/${ZIG_DIR}/lib" /usr/local/lib/zig
        rm -rf "/tmp/${ZIG_TARBALL}" "/tmp/${ZIG_DIR}"
        echo "Zig ${ZIG_VERSION} installed."
    fi
    
    # Clone and build fssimu2
    if [ -d "fssimu2" ]; then rm -rf fssimu2; fi
    git clone https://github.com/gianni-rosato/fssimu2.git
    cd fssimu2
    
    echo "Building fssimu2 with Zig..."
    zig build --release=fast --prefix /usr/local
    
    cd ..
    rm -rf fssimu2
    
    if command -v fssimu2 &> /dev/null; then
        echo "fssimu2 installed successfully to /usr/local/bin/fssimu2"
    else
        echo "WARNING: fssimu2 build may have failed. Check for errors above."
    fi
else
    echo "fssimu2 is already installed."
fi

# Create a build directory
mkdir -p build_tmp
cd build_tmp

# 6. SVT-AV1-PSY (Optimized Build)
if ! command -v SvtAv1EncApp &> /dev/null; then
    echo "=========================================================="
    echo "Compiling SVT-AV1-PSY (5fish Fork - Anime Optimized)..."
    echo "Using Clang + PGO + LTO for maximum performance."
    echo "=========================================================="
    
    # Ensure llvm-profdata is found (required for PGO)
    if ! command -v llvm-profdata &> /dev/null; then
        echo "llvm-profdata not found in PATH. Searching for versioned binary..."
        # Find latest llvm-profdata (e.g., llvm-profdata-18)
        LLVM_PROFDATA=$(find /usr/bin -name "llvm-profdata-*" | sort -V | tail -n 1)
        if [ -n "$LLVM_PROFDATA" ]; then
            echo "Found $LLVM_PROFDATA. Creating symlink to /usr/local/bin/llvm-profdata"
            ln -sf "$LLVM_PROFDATA" /usr/local/bin/llvm-profdata
            ln -sf "${LLVM_PROFDATA}" /usr/bin/llvm-profdata # Fallback
        else
            echo "WARNING: llvm-profdata not found. PGO might fail."
        fi
    fi

    if [ -d "svt-av1-psy" ]; then rm -rf svt-av1-psy; fi
    git clone -b ac-bias+exp https://github.com/5fish/svt-av1-psy.git
    cd svt-av1-psy
    git checkout e87a5ae3 || echo "Warning: Commit e87a5ae3 not found. Using latest tip of ac-bias+exp."
    
    mkdir -p Build/linux
    cd Build/linux
    
    cmake ../.. -G"Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
        -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
        -DSVT_AV1_PGO=ON -DSVT_AV1_LTO=ON
    
    make -j $(nproc)
    make install
    
    cd ../../..
else
    echo "SvtAv1EncApp is already installed."
fi

# 7. WWXD
# Find where vapoursynth plugins go.
if command -v pkg-config &> /dev/null; then
    VS_PLUGIN_PATH=$(pkg-config --variable=libdir vapoursynth)/vapoursynth
else
    # Fallback
    VS_PLUGIN_PATH="/usr/lib/x86_64-linux-gnu/vapoursynth"
    if [ "$DISTRO" == "arch" ]; then VS_PLUGIN_PATH="/usr/lib/vapoursynth"; fi
fi
mkdir -p "$VS_PLUGIN_PATH"

# 6b. VapourSynth-WWXD (Scene detection)
echo "Compiling VapourSynth-WWXD..."
if [ -d "vapoursynth-wwxd" ]; then rm -rf vapoursynth-wwxd; fi
git clone https://github.com/dubhater/vapoursynth-wwxd.git
cd vapoursynth-wwxd

# Compile manually since waf might be missing
# Include /usr/local/include/vapoursynth so <VapourSynth.h> is found
gcc -o libwwxd.so -fPIC -shared -O3 -Wall -Wextra -I. -I/usr/local/include/vapoursynth src/*.c -lm

# Install to standard and logical paths to ensure visibility
cp libwwxd.so "$VS_PLUGIN_PATH/"
if [ -d "/usr/lib/x86_64-linux-gnu/vapoursynth" ]; then
    cp libwwxd.so "/usr/lib/x86_64-linux-gnu/vapoursynth/"
fi
echo "WWXD installed to $VS_PLUGIN_PATH"
cd ..

# 7. VSZIP (Required for Metrics)
echo "Compiling VSZIP..."
if [ -d "vszip" ]; then rm -rf vszip; fi
# Use dnjulek/vapoursynth-zip (Active fork)
git clone https://github.com/dnjulek/vapoursynth-zip.git vszip
cd vszip

# Download Portable Zig (Linux x86_64) - handled by repo script now
cd build-help
chmod +x build.sh
./build.sh

# Correctly place the plugin (build.sh puts it in /usr/lib/vapoursynth)
if [ -f "../zig-out/lib/libvszip.so" ]; then
    echo "Installing VSZIP to verified plugin path..."
    cp "../zig-out/lib/libvszip.so" "$VS_PLUGIN_PATH/libvszip.so"
    
    # Ensure fallback path also has it
    if [ -d "/usr/lib/x86_64-linux-gnu/vapoursynth" ]; then
        cp "../zig-out/lib/libvszip.so" "/usr/lib/x86_64-linux-gnu/vapoursynth/libvszip.so"
    fi
    echo "VSZIP installed successfully."
else
    echo "ERROR: VSZIP Compilation failed!"
fi
cd ../..
    
    # Refresh libs
    ldconfig

# Cleanup
cd ..
rm -rf build_tmp

echo ""
echo "=========================================================="
echo "   Installation Complete!"
echo "=========================================================="
echo "Supported Distro Setup Finished: $DISTRO"
echo "Please verify tools are in PATH."
