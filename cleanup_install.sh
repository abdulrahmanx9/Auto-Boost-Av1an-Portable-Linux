#!/bin/bash

echo "=========================================================="
echo "   Auto-Boost-Av1an Deep Cleanup Script"
echo "=========================================================="
echo "This script wipes ALL dependencies installed by install_deps_ubuntu.sh"
echo "Including VapourSynth, Av1an, SVT-AV1, FFMS2, and Python Libs."
echo "USE WITH CAUTION."
echo ""

if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo ./cleanup_install.sh)"
    exit 1
fi

read -p "Are you sure you want to WIPEOUT all these tools? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "Cleaning up..."

# 1. Binaries
echo "- Removing Binaries..."
rm -vf /usr/local/bin/av1an
rm -vf /usr/local/bin/SvtAv1EncApp
rm -vf /usr/local/bin/vspipe
rm -vf /usr/local/bin/llvm-profdata

# 2. Libraries
echo "- Removing Libraries..."
rm -vf /usr/local/lib/libvapoursynth*
rm -vf /usr/local/lib/libSvtAv1Enc*
rm -vf /usr/local/lib/libffms2*
rm -vf /usr/local/lib/vapoursynth.so # Python module sometimes here

# 3. Headers
echo "- Removing Headers..."
rm -rf /usr/local/include/vapoursynth
rm -rf /usr/local/include/svt-av1
rm -rf /usr/local/include/ffms2

# 4. Plugins
echo "- Removing VapourSynth Plugins..."
rm -rf /usr/local/lib/vapoursynth  # This contains wwxd, vszip usually
rm -rf /usr/lib/x86_64-linux-gnu/vapoursynth # Fallback path used by installer

# 4b. Python Module Symlink (Manual Install)
rm -vf /usr/lib/python3/dist-packages/vapoursynth.so

# 5. PkgConfig
echo "- Removing PkgConfig files..."
rm -vf /usr/local/lib/pkgconfig/vapoursynth.pc
rm -vf /usr/local/lib/pkgconfig/SvtAv1Enc.pc
rm -vf /usr/local/lib/pkgconfig/ffms2.pc

# 6. Python Libraries
echo "- Uninstalling Python Libraries..."
pip3 uninstall -y vapoursynth vsjetpack numpy rich vstools psutil --break-system-packages

# 7. Build Directoru
if [ -d "build_tmp" ]; then
    echo "- Removing build_tmp..."
    rm -rf build_tmp
fi

# 8. Refresh Cache
ldconfig

echo ""
echo "Additional Cleanup:"
echo "If you want to remove Rust completely: 'rustup self uninstall'"
echo "If you want to remove Av1an from user cargo: 'cargo uninstall av1an'"
echo ""
echo "Cleanup Complete. System should be clean for a fresh run."
