import os
import sys
import re
import subprocess
import glob
from wakepy import keep


def main():
    # --- Configuration Paths ---
    # Determine paths relative to this script location (tools/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tools_dir = script_dir  # This script is inside tools/

    # --- Step 0: Detect Active Batch via Marker ---
    # We look for files created by the shell scripts: bat-used-Progression-Boost-SSIMU2-*.txt
    # We keep "bat-used" prefix for compatibility or adapt to "sh-used" if we change shell script.
    # Let's assume shell script creates "sh-used-Progression-Boost-SSIMU2-*.txt" or we reuse "bat-used".
    # I will stick to "bat-used" to minimize changes if the python script logic is reused elsewhere,
    # BUT since I am rewriting it, I will look for *.txt markers generally or specifically "sh-used-".
    # Let's stick to "bat-used" for consistency with the Windows logic if possible, or just "active-job-".
    # I will Update Shell Script to create "bat-used-Progression-Boost-SSIMU2-anime.sh.txt"

    marker_pattern = os.path.join(tools_dir, "bat-used-Progression-Boost-SSIMU2-*.txt")
    markers = glob.glob(marker_pattern)

    suffix = None

    if not markers:
        print("[Dispatch] Warning: No active batch marker found in tools/.")
        print("[Dispatch] Cannot determine if Anime or LiveAction is intended.")
        print("[Dispatch] Defaulting to 'anime' workflow as fallback.")
        suffix = "anime"
    else:
        # If multiple exist, pick the most recently created/modified one
        latest_marker = max(markers, key=os.path.getctime)
        filename = os.path.basename(latest_marker)

        # Expected filename format: bat-used-Progression-Boost-SSIMU2-[TYPE].sh.txt
        if "anime" in filename.lower():
            suffix = "anime"
        elif "liveaction" in filename.lower():
            suffix = "liveaction"
        else:
            print(
                f"[Dispatch] Warning: Could not identify type from marker '{filename}'. Defaulting to anime."
            )
            suffix = "anime"

    print(f"[Dispatch] Mode detected: {suffix.upper()}")

    # Define target filenames based on the detected suffix
    # Shell Name: Progression-Boost-SSIMU2-anime.sh
    # Python Name: Progression-Boost-Basic-SSIMU2-anime.py

    batch_filename = f"Progression-Boost-SSIMU2-{suffix}.sh"
    python_filename = f"Progression-Boost-Basic-SSIMU2-{suffix}.py"

    # The shell file is one level up from "tools"
    batch_file_path = os.path.join(script_dir, "..", batch_filename)

    # The target python script is in the same "tools" folder
    target_script_path = os.path.join(script_dir, python_filename)

    # --- Step 1: Read Quality Setting from Shell File ---
    quality_val = "85"  # Default fallback

    try:
        with open(batch_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Look for: ssimu2_quality=XX or ssimu2-quality=XX
            match = re.search(r'ssimu2[-_]quality=["\']?(\d+)["\']?', content)
            if match:
                quality_val = match.group(1)
                print(
                    f"[Dispatch] Found quality target in {batch_filename}: {quality_val}"
                )
            else:
                print(
                    f"[Dispatch] Warning: 'ssimu2-quality' not found in {batch_filename}. Using default."
                )
    except FileNotFoundError:
        print(f"[Dispatch] Error: Shell file not found at {batch_file_path}")

    # --- Step 1.5: Read Worker/Tool Config ---
    # Determine if we should use vs-hip (vship), vs-zip (vszip), or fssimu2
    workercount_path = os.path.join(tools_dir, "workercount-ssimu2.txt")
    tool_mode = "vs-hip"  # Default fallback if no config exists

    if os.path.exists(workercount_path):
        try:
            with open(workercount_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Check for explicit tool definitions
                if "tool=vs-zip" in content:
                    tool_mode = "vs-zip"
                elif "tool=fssimu2" in content:
                    tool_mode = "fssimu2"
                elif "tool=vs-hip" in content:
                    tool_mode = "vs-hip"
        except Exception as e:
            print(f"[Dispatch] Warning: Could not read workercount-ssimu2.txt: {e}")

    print(f"[Dispatch] SSIMULACRA2 Tool Configuration: {tool_mode}")

    # --- Step 2: Edit the Target Python Script ---
    # We update the metric_target AND comment/uncomment blocks based on tool_mode

    target_marker = "# Maybe set it a little bit lower than your actual target."
    vship_marker = "vship, uncomment the lines below."
    vszip_marker = "via vszip, uncomment the lines below."

    output_lines = []

    try:
        with open(target_script_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        iterator = iter(lines)
        modified = False

        for line in iterator:
            # 1. Handle Quality Target Update
            if target_marker in line:
                output_lines.append(line)
                try:
                    old_line = next(iterator)
                    indent = ""
                    indent_match = re.match(r"^(\s*)", old_line)
                    if indent_match:
                        indent = indent_match.group(1)
                    output_lines.append(f"{indent}metric_target = {quality_val}.000\n")
                    modified = True
                except StopIteration:
                    pass
                continue

            # 2. Handle vship block (approx 6 lines)
            if vship_marker in line:
                output_lines.append(line)
                for _ in range(6):
                    try:
                        l = next(iterator)
                        if tool_mode in ["vs-hip", "fssimu2"]:
                            # Ensure UNCOMMENTED (Remove leading # and optional space)
                            if l.strip().startswith("#"):
                                l = re.sub(r"^(\s*)#\s?(.*)", r"\1\2", l)
                        else:
                            # Ensure COMMENTED (Add # and space if not present)
                            if not l.strip().startswith("#") and l.strip() != "":
                                l = re.sub(r"^(\s*)(.*)", r"\1# \2", l)
                        output_lines.append(l)
                        modified = True
                    except StopIteration:
                        break
                continue

            # 3. Handle vszip block (approx 4 lines)
            if vszip_marker in line:
                output_lines.append(line)
                for _ in range(4):
                    try:
                        l = next(iterator)
                        if tool_mode == "vs-zip":
                            # Ensure UNCOMMENTED
                            if l.strip().startswith("#"):
                                l = re.sub(r"^(\s*)#\s?(.*)", r"\1\2", l)
                        else:
                            # Ensure COMMENTED
                            if not l.strip().startswith("#") and l.strip() != "":
                                l = re.sub(r"^(\s*)(.*)", r"\1# \2", l)
                        output_lines.append(l)
                        modified = True
                    except StopIteration:
                        break
                continue

            # 4. Handle Binary Name Replacement (FFVship -> vship or fssimu2)
            # Look for: command = ["FFVship", or "vship", or "fssimu2",
            binary_match = re.search(
                r'command\s*=\s*\[\s*"(FFVship|vship|fssimu2)"', line
            )
            if binary_match:
                active_binary = "FFVship"  # Default fallback
                if tool_mode == "fssimu2":
                    active_binary = "fssimu2"
                elif tool_mode == "vs-hip":
                    active_binary = "FFVship"

                # If we have a preferred binary, perform substitution
                if active_binary != binary_match.group(1):
                    line = line.replace(
                        f'"{binary_match.group(1)}"', f'"{active_binary}"'
                    )
                    modified = True

            output_lines.append(line)

        if modified:
            with open(target_script_path, "w", encoding="utf-8") as f:
                f.writelines(output_lines)
            print(
                f"[Dispatch] Updated {python_filename} (Quality: {quality_val}, Tool: {tool_mode})"
            )
        else:
            print(
                f"[Dispatch] Warning: No changes made to {python_filename}. Check markers."
            )

    except FileNotFoundError:
        print(f"[Dispatch] Error: Target script not found at {target_script_path}")
        sys.exit(1)

    # --- Step 3: Run the Target Python Script ---
    print(f"[Dispatch] Launching {python_filename}...")
    print("-" * 60)

    cmd = [sys.executable, target_script_path] + sys.argv[1:]

    try:
        sys.stdout.flush()
        print("[Dispatch] Preventing system sleep via wakepy...")
        with keep.running():
            subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
