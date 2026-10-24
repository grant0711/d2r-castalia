#!/usr/bin/env bash
# Shared environment and helper functions for Diablo II: Resurrected on Ubuntu + i3
set -euo pipefail

export D2R_ROOT="/home/grant/games/d2r"
export UMU_RUN="${D2R_ROOT}/runtime/umu/umu-run"
export PROTON_DIR="${D2R_ROOT}/runtime/proton/GE-Proton11-11"
export GAME_DIR="${D2R_ROOT}/game/Diablo II Resurrected"
export BNET_INSTALLER="${D2R_ROOT}/tools/Battle.net-Setup.exe"

# Raise open file descriptors limit for Proton esync/fsync
ulimit -n 1048576 2>/dev/null || true

# NVIDIA Quadro P5200 PRIME Render Offload environment variables
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __VK_LAYER_NV_optimus=NVIDIA_only
export VK_ICD_FILENAMES="/usr/share/vulkan/icd.d/nvidia_icd.json"

# Proton / Wine optimizations for Battle.net + D2R
export GAMEID="umu-d2r"
export STORE="battlenet"
export PROTON_NO_ESYNC=0
export PROTON_NO_FSYNC=0
export DXVK_ASYNC=1
export VKD3D_CONFIG="dxr"
export WINE_LARGE_ADDRESS_AWARE=1

# Run via umu-run (SteamLinuxRuntime container) if unprivileged user namespaces are allowed,
# or fall back automatically to direct GE-Proton execution with steamrt4's library paths appended.
run_proton() {
    ensure_proton
    echo "${WINEPREFIX}" > "${D2R_ROOT}/prefixes/.active_prefix" 2>/dev/null || true
    export STEAM_COMPAT_DATA_PATH="${WINEPREFIX}"
    export STEAM_COMPAT_CLIENT_INSTALL_PATH="${D2R_ROOT}/runtime"
    if [ "$(sysctl -n kernel.apparmor_restrict_unprivileged_userns 2>/dev/null || echo 0)" = "0" ]; then
        exec "${UMU_RUN}" "$@"
    else
        # Append steamrt4 64-bit and 32-bit libraries (libfreetype, libfontconfig, libpulse, libXrandr, etc.)
        # AFTER host libraries so host glibc/NVIDIA drivers take precedence while missing 32-bit libs resolve cleanly
        local srt_dir
        srt_dir="$(find /home/grant/.local/share/umu/steamrt4 -maxdepth 1 -type d -name 'steamrt4_platform_*' 2>/dev/null | head -n 1 || true)"
        if [ -n "${srt_dir}" ] && [ -d "${srt_dir}/files/lib" ]; then
            if [ ! -e "${srt_dir}/files/lib/i386-linux-gnu/libfreetype.so.6" ]; then
                /sbin/ldconfig -n "${srt_dir}/files/lib/i386-linux-gnu" \
                                  "${srt_dir}/files/lib/x86_64-linux-gnu" \
                                  "${srt_dir}/files/lib/i386-linux-gnu/pulseaudio" \
                                  "${srt_dir}/files/lib/x86_64-linux-gnu/pulseaudio" 2>/dev/null || true
            fi
            local srt_libs="${srt_dir}/files/lib/x86_64-linux-gnu:${srt_dir}/files/lib/i386-linux-gnu:${srt_dir}/files/lib/i386-linux-gnu/pulseaudio:${srt_dir}/files/lib/x86_64-linux-gnu/pulseaudio"
            export LD_LIBRARY_PATH="/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:/lib/i386-linux-gnu:/usr/lib/i386-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}:${srt_libs}"
        fi
        exec "${PROTON_DIR}/proton" run "$@"
    fi
}
ensure_proton() {
    if [ ! -d "${PROTON_DIR}" ]; then
        echo "[d2r] GE-Proton11-11 not found yet. Downloading (~450 MB)..."
        mkdir -p "${D2R_ROOT}/runtime/proton"
        curl -L --progress-bar -o "${D2R_ROOT}/runtime/proton/GE-Proton11-11.tar.gz" \
            "https://github.com/GloriousEggroll/proton-ge-custom/releases/download/GE-Proton11-11/GE-Proton11-11-x86_64.tar.gz"
        echo "[d2r] Extracting GE-Proton11-11..."
        tar -xzf "${D2R_ROOT}/runtime/proton/GE-Proton11-11.tar.gz" -C "${D2R_ROOT}/runtime/proton/"
        rm -f "${D2R_ROOT}/runtime/proton/GE-Proton11-11.tar.gz"
    fi
    export PROTONPATH="${PROTON_DIR}"
}

# Link shared D2R game folder into a Proton prefix so both accounts share 1 installation
link_shared_game_dir() {
    local prefix_dir="$1"
    local pfx_c="${prefix_dir}/pfx/drive_c"
    mkdir -p "${pfx_c}/Program Files (x86)"
    mkdir -p "${GAME_DIR}"

    # Link C:\Program Files (x86)\Diablo II Resurrected -> shared GAME_DIR
    local target_pf="${pfx_c}/Program Files (x86)/Diablo II Resurrected"
    if [ ! -L "${target_pf}" ]; then
        if [ -d "${target_pf}" ] && [ -f "${target_pf}/D2R.exe" ] && [ ! -f "${GAME_DIR}/D2R.exe" ]; then
            echo "[d2r] Moving installed D2R files from prefix into shared ${GAME_DIR}..."
            cp -a "${target_pf}/." "${GAME_DIR}/"
        fi
        rm -rf "${target_pf}"
        ln -s "${GAME_DIR}" "${target_pf}"
    fi

    # Also create short path C:\D2R -> shared GAME_DIR
    if [ ! -L "${pfx_c}/D2R" ]; then
        rm -rf "${pfx_c}/D2R"
        ln -s "${GAME_DIR}" "${pfx_c}/D2R"
    fi
}
