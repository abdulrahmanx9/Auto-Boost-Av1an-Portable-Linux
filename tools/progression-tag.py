import os
import glob
import re
import subprocess
import tempfile
import sys
import shutil


# --- GLOBALS ---
# We assume 'mkvpropedit' is in the system PATH or in tools/MKVToolNix
def get_binary(name):
    # Try system path first
    path = shutil.which(name)
    if path:
        return path
    # Try tools folder
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming standard Linux layout, tools/ is script_dir
    # But files might be in tools/MKVToolNix/ or similar if ported directly
    # Check simple relative path
    local_path = os.path.join(script_dir, name)
    if os.path.exists(local_path):
        return local_path

    return name  # Fallback to name


MKVPROPEDIT = get_binary("mkvpropedit")


def get_5fish_folder():
    """Finds the 5fish folder name in tools/av1an."""
    base_path = os.path.join("tools", "av1an")
    # Search for folder starting with 5fish-svt-av1-psy
    pattern = os.path.join(base_path, "5fish-svt-av1-psy*")
    folders = glob.glob(pattern)
    if folders:
        return os.path.basename(folders[0])
    return "5fish-svt-av1-psy_Unknown"


def get_active_batch_info():
    """
    Scans tools/ for the marker file to determine the batch name.
    Returns (batch_name_clean, marker_file_path).
    """
    pattern = os.path.join("tools", "bat-used-*.txt")
    files = glob.glob(pattern)

    if not files:
        print(
            "Error: No active batch marker found in tools/. Cannot determine settings."
        )
        return None, None

    # If multiple, pick the newest
    marker_file = max(files, key=os.path.getctime)
    filename = os.path.basename(marker_file)

    # Expected format: bat-used-[NAME].sh.txt or bat-used-[NAME].txt
    # 1. Remove prefix
    temp_name = filename.replace("bat-used-", "")
    # 2. Remove .txt suffix
    if temp_name.lower().endswith(".txt"):
        temp_name = temp_name[:-4]

    # 3. Remove .sh or .bat if present in the stem
    batch_name_clean = temp_name
    if batch_name_clean.lower().endswith(".sh"):
        batch_name_clean = batch_name_clean[:-3]
    elif batch_name_clean.lower().endswith(".bat"):
        batch_name_clean = batch_name_clean[:-4]

    return batch_name_clean, marker_file


def parse_batch_for_quality(batch_name):
    """
    Reads the .sh file to find ssimu2-quality value.
    """
    # Try looking for the shell file in root or tools
    candidates = [
        f"{batch_name}.sh",
        os.path.join("tools", f"{batch_name}.sh"),
        os.path.join("..", f"{batch_name}.sh"),
    ]
    batch_path = None

    for c in candidates:
        if os.path.exists(c):
            batch_path = c
            break

    quality = "Unknown"

    if batch_path:
        try:
            with open(batch_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Look for ssimu2_quality=84 or ssimu2-quality=84
                match = re.search(r'ssimu2[-_]quality=["\']?(\d+)["\']?', content)
                if match:
                    quality = match.group(1)
        except Exception as e:
            print(f"Warning: Could not read shell file {batch_path}: {e}")

    return quality


def find_python_script(batch_name):
    """
    Locates the python automation script corresponding to the batch.
    """
    candidates = []

    # 1. Exact match: tools/[Name].py
    candidates.append(os.path.join("tools", f"{batch_name}.py"))

    # 2. "Basic" injection
    if "SSIMU2" in batch_name and "Basic" not in batch_name:
        basic_name = batch_name.replace("SSIMU2", "Basic-SSIMU2")
        candidates.append(os.path.join("tools", f"{basic_name}.py"))

    # 3. Check root/parent folder
    candidates.append(f"{batch_name}.py")
    if "SSIMU2" in batch_name and "Basic" not in batch_name:
        basic_name = batch_name.replace("SSIMU2", "Basic-SSIMU2")
        candidates.append(f"{basic_name}.py")

    for p in candidates:
        if os.path.exists(p):
            return p

    return None


def extract_dynamic_params(script_path):
    """
    Reads the python script and extracts the return string from final_dynamic_parameters.
    """
    if not script_path or not os.path.exists(script_path):
        print(f"Warning: Python script '{script_path}' not found.")
        return ""

    params = ""
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = r'def\s+final_dynamic_parameters.*?return\s+"""(.*?)"""'

        match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
        if match:
            raw_params = match.group(1)
            lines = [line.strip() for line in raw_params.splitlines()]
            params = " ".join(filter(None, lines))
        else:
            # Fallback
            pattern_loose = (
                r'def\s+final_dynamic_parameters.*?return\s+[\'"]{3}(.*?)[\'"]{3}'
            )
            match_loose = re.search(pattern_loose, content, re.DOTALL | re.MULTILINE)
            if match_loose:
                raw_params = match_loose.group(1)
                lines = [line.strip() for line in raw_params.splitlines()]
                params = " ".join(filter(None, lines))

    except Exception as e:
        print(f"Error parsing python script {script_path}: {e}")

    return params


def apply_tag_to_file(filepath, tag_string):
    """Generates XML and uses mkvpropedit to tag the file."""
    xml_template = f"""<?xml version="1.0"?>
<Tags>
  <Tag>
    <Targets>
      <TrackUID>1</TrackUID>
    </Targets>
    <Simple>
      <Name>ENCODING_SETTINGS</Name>
      <String>{tag_string}</String>
    </Simple>
  </Tag>
</Tags>
"""
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".xml", mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(xml_template)
        tmp_path = tmp.name

    try:
        print(f"Applying tag to: {filepath}")
        cmd = [MKVPROPEDIT, filepath, "--tags", "track:v1:" + tmp_path]

        subprocess.run(cmd, check=True, capture_output=True)
        print("Success.")
    except subprocess.CalledProcessError as e:
        print(f"Error tagging {filepath}: {e}")
        if e.stderr:
            print(f"Details: {e.stderr.decode('utf-8')}")
    except FileNotFoundError:
        print(f"Error: {MKVPROPEDIT} not found.")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def main():
    print("Progression Tagging Process Initialized...")

    batch_name, marker_path = get_active_batch_info()
    if not batch_name:
        return

    ssimu2_q = parse_batch_for_quality(batch_name)
    python_script_path = find_python_script(batch_name)
    dynamic_params = extract_dynamic_params(python_script_path)

    if not dynamic_params:
        print("Warning: Could not extract dynamic parameters.")

    fish_ver = get_5fish_folder()

    full_tag = (
        f"{batch_name} "
        f"metric_target = {ssimu2_q} "
        f"{fish_ver} "
        f'settings: "--preset 2 {dynamic_params}"'
    )

    print(
        "-------------------------------------------------------------------------------"
    )
    print(f"Detected Batch : {batch_name}")
    print(f"Python Script  : {python_script_path}")
    print(f"SSIMU2 Target  : {ssimu2_q}")
    print(f"Generated Tag  :\n{full_tag}")
    print(
        "-------------------------------------------------------------------------------"
    )

    target_files = glob.glob("*-av1.mkv")

    if not target_files:
        print("No output *-av1.mkv files found to tag.")
    else:
        for f in target_files:
            apply_tag_to_file(f, full_tag)

    if marker_path and os.path.exists(marker_path):
        try:
            os.remove(marker_path)
            print("Batch marker removed.")
        except OSError as e:
            print(f"Warning: Could not delete marker {marker_path}: {e}")


if __name__ == "__main__":
    main()
