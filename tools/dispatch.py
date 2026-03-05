import sys
import subprocess
import os
import shutil

try:
    from wakepy import keep

    WAKEPY_AVAILABLE = True
except ImportError:
    WAKEPY_AVAILABLE = False


def main():
    # --- Configuration ---
    # Determine paths relative to this script (Linux_Dist/tools/dispatch.py)
    script_path = os.path.abspath(__file__)
    tools_dir = os.path.dirname(script_path)
    root_dir = os.path.dirname(tools_dir)

    # Path to av1an script
    av1an_script = os.path.join(root_dir, "Auto-Boost-Av1an.py")

    # Locate MediaInfo (Linux System Path)
    mediainfo_exe = shutil.which("mediainfo")

    # --- Argument Parsing ---
    # Find input file (-i or --input)
    args = sys.argv[1:]
    input_file = None

    for idx, arg in enumerate(args):
        if arg in ("-i", "--input") and idx + 1 < len(args):
            input_file = args[idx + 1]
            break

    # --- Color Space Detection via MediaInfo ---
    is_bt709 = False
    is_bt601 = False

    # Flags to track BT.709
    f_prim_709 = False
    f_trans_709 = False
    f_mat_709 = False

    # Flags to track BT.601
    f_prim_601 = False
    f_trans_601 = False
    f_mat_601 = False

    if input_file and os.path.exists(input_file):
        if mediainfo_exe:
            try:
                # Run MediaInfo on the file
                cmd = [mediainfo_exe, input_file]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                )

                if result.returncode == 0:
                    # Parse the text output line by line
                    for line in result.stdout.splitlines():
                        if ":" not in line:
                            continue

                        # Split into Key : Value
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()

                        # Check Color Primaries
                        if key == "Color primaries":
                            if value == "BT.709":
                                f_prim_709 = True
                            elif "BT.601" in value:
                                f_prim_601 = True

                        # Check Transfer characteristics
                        elif key == "Transfer characteristics":
                            if value == "BT.709":
                                f_trans_709 = True
                            elif "BT.601" in value:
                                f_trans_601 = True

                        # Check Matrix coefficients
                        elif key == "Matrix coefficients":
                            if value == "BT.709":
                                f_mat_709 = True
                            elif "BT.601" in value:
                                f_mat_601 = True

                    # Evaluate Detection
                    if f_prim_709 and f_trans_709 and f_mat_709:
                        is_bt709 = True
                        print("[Dispatch] MediaInfo confirmed full BT.709 source.")
                    elif f_prim_601 and f_trans_601 and f_mat_601:
                        is_bt601 = True
                        print("[Dispatch] MediaInfo confirmed full BT.601 source.")
                    else:
                        print(
                            f"[Dispatch] MediaInfo results - 709: ({f_prim_709},{f_trans_709},{f_mat_709}) | 601: ({f_prim_601},{f_trans_601},{f_mat_601}). No standard color match."
                        )
                else:
                    print("[Dispatch] Warning: MediaInfo returned an error.")
            except Exception as e:
                print(f"[Dispatch] Warning: MediaInfo execution failed: {e}")
        else:
            print("[Dispatch] Warning: mediainfo not found in PATH.")
            print("[Dispatch] Install it with: sudo apt install mediainfo")

    # --- Check for special flags ---
    # v1.5: --convert-to-YUV420P10 for non-standard chroma subsampling (4:2:2, 4:4:4, etc.)
    convert_yuv420p10 = (
        "--convert-to-YUV420P10" in args or "--convert-to-yuv420p10" in args
    )
    if convert_yuv420p10:
        print(
            "[Dispatch] YUV420P10 conversion enabled for non-standard chroma subsampling."
        )

    # --- Construct Final Command ---
    # Use standard python3
    final_cmd = ["python3", av1an_script]

    # Parameters to inject
    # Note: BT.601 parameters set to 6-6-6
    bt709_flags = (
        " --color-primaries 1 --transfer-characteristics 1 --matrix-coefficients 1"
    )
    bt601_flags = (
        " --color-primaries 6 --transfer-characteristics 6 --matrix-coefficients 6"
    )

    current_flags = ""
    if is_bt709:
        print("[Dispatch] Injecting BT.709 parameters.")
        current_flags = bt709_flags
    elif is_bt601:
        print("[Dispatch] Injecting BT.601 parameters.")
        current_flags = bt601_flags
    else:
        print("[Dispatch] Using standard parameters (no color injection).")

    skip_next = False
    for idx, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue

        # If we find the parameter strings, append flags if needed
        if arg in ("--fast-params", "--final-params"):
            final_cmd.append(arg)
            if idx + 1 < len(args):
                param_str = args[idx + 1]
                # Append detected flags to the existing string
                if current_flags:
                    param_str += current_flags
                final_cmd.append(param_str)
                skip_next = True
            else:
                final_cmd.append("")
        else:
            final_cmd.append(arg)

    # --- Execute ---
    try:
        sys.stdout.flush()

        if WAKEPY_AVAILABLE:
            print("[Dispatch] Preventing system sleep via wakepy...")
            # Wrap the encoding process in wakepy's keep.running() context
            with keep.running():
                subprocess.check_call(final_cmd)
        else:
            print("[Dispatch] wakepy not available, system may sleep during encoding.")
            subprocess.check_call(final_cmd)

    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(f"Error: Could not execute {av1an_script}. Check file paths.")
        sys.exit(1)


if __name__ == "__main__":
    main()
