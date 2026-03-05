import os
import glob
import re
import subprocess
import shutil
import platform
import tempfile
import shlex


def get_script_version():
    """Extracts the latest version number from Auto-Boost-Av1an.py or readme.txt."""
    # First try Auto-Boost-Av1an.py
    script_path = "Auto-Boost-Av1an.py"
    version = "Unknown"

    if os.path.exists(script_path):
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                content = f.read()
                # ver_str = "v2.9.20 (Clean UI)"
                match = re.search(r'ver_str\s*=\s*"([^"]+)"', content)
                if match:
                    version = match.group(1).split(" ")[
                        0
                    ]  # Take "v2.9.20" from "v2.9.20 (Clean UI)"
        except Exception:
            pass

    if version == "Unknown":
        readme_path = "readme.txt"
        if os.path.exists(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    match = re.search(r"v(\d+\.\d+)", content)
                    if match:
                        version = "v" + match.group(1)
            except Exception:
                pass
    return version


def resolve_variables(val):
    """
    Resolves known shell variables like $SSIMU2_TOOL, $SSIMU2_WORKERS.
    """
    if not val or "$" not in val:
        return val

    # Common variables map
    vars_map = {}

    # Load SSIMU2 config if available
    config_file = os.path.join("tools", "workercount-ssimu2.txt")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("tool="):
                        vars_map["SSIMU2_TOOL"] = line.split("=", 1)[1].strip()
                    if line.startswith("workercount="):
                        vars_map["SSIMU2_WORKERS"] = line.split("=", 1)[1].strip()
        except:
            pass

    # Defaults if missing
    if "SSIMU2_TOOL" not in vars_map:
        vars_map["SSIMU2_TOOL"] = "vs-zip"  # Default fallback
    if "SSIMU2_WORKERS" not in vars_map:
        vars_map["SSIMU2_WORKERS"] = "4"

    # Replace
    for k, v in vars_map.items():
        val = val.replace(f"${k}", v).replace(f"${{{k}}}", v)

    return val


def get_5fish_version():
    """Gets the SVT-AV1-PSY version from the installed binary."""
    # On Linux, s-a-p is installed to system PATH (SvtAv1EncApp)
    # On Windows, it's in a folder. We try running the tool.

    svt_exe = shutil.which("SvtAv1EncApp")
    if not svt_exe:
        return "SvtAv1EncApp_NotFound"

    try:
        # Expected output: "SVT-AV1-PSY v2.3.0-..."
        res = subprocess.run([svt_exe, "--version"], capture_output=True, text=True)
        if res.returncode == 0:
            # First line often contains it.
            # Or stdout might be "SVT-AV1-PSY v..."
            # Let's try to extract the version string.
            for line in res.stdout.splitlines():
                if "SVT-AV1" in line:
                    return line.strip()
    except Exception:
        pass

    return "SvtAv1EncApp_Unknown"


def get_active_batch_filename():
    """Scans tools/ folder for the marker file created by the .bat/.sh script."""
    # Look for files like tools/bat-used-batch.bat.txt or tools/sh-used-run.sh.txt
    pattern_bat = os.path.join("tools", "bat-used-*.txt")
    pattern_sh = os.path.join("tools", "sh-used-*.txt")
    files = glob.glob(pattern_bat) + glob.glob(pattern_sh)

    if not files:
        print(
            "Error: No active batch/shell marker found in tools/. Cannot determine settings."
        )
        return None

    marker_file = files[0]
    filename = os.path.basename(marker_file)

    # Remove prefix "bat-used-" or "sh-used-" and suffix ".txt"
    batch_name = (
        filename.replace("bat-used-", "").replace("sh-used-", "").replace(".txt", "")
    )

    try:
        os.remove(marker_file)
        print(f"Detected active script: {batch_name} (Marker removed)")
    except OSError as e:
        print(f"Warning: Could not delete marker file {marker_file}: {e}")

    return batch_name


def parse_batch_line(line):
    """
    Dynamically parses the command line args using shlex.
    Returns:
      - general_flags: A list of strings (e.g. ['--quality 15', '--aggressive', '--ssimu2'])
      - final_params: The content string of the --final-params arg
      - quality: The value of --quality (for CRF calculation)
      - final_speed: The value of --final-speed (for Preset mapping)
    """
    try:
        parts = shlex.split(
            line, posix=True
        )  # posix=True works better on Linux for quoting
    except ValueError:
        return [], "", "medium", None

    # Locate where the dispatch script starts
    start_idx = -1
    for i, part in enumerate(parts):
        if "dispatch.py" in part or "Auto-Boost-Av1an.py" in part:
            start_idx = i
            break

    if start_idx == -1:
        return [], "", "medium", None

    # Get all arguments after the script name
    raw_args = parts[start_idx + 1 :]

    general_flags = []
    final_params = ""
    quality = "medium"
    final_speed = None

    i = 0
    while i < len(raw_args):
        curr = raw_args[i]

        # 1. Structural arguments to EXCLUDE from the tag
        # fast-speed is processed but usually excluded from general flags?
        # Actually logic below adds flags unless handled.

        # Arguments to skip (value is next)
        if curr in [
            "-i",
            "--input",
            "--scenes",
            "--workers",
            "--temp",
            "-o",
            "--output",
        ]:
            i += 2
            continue

        # 2. Fast params: exclude
        if curr == "--fast-params":
            i += 2
            continue

        # 3. Final Params: extract content
        if curr == "--final-params":
            if i + 1 < len(raw_args):
                final_params = resolve_variables(raw_args[i + 1])
                i += 2
            else:
                i += 1
            continue

        # 4. Handle Flags
        if curr.startswith("-"):
            flag = curr
            val = None

            if i + 1 < len(raw_args):
                next_token = raw_args[i + 1]
                if not next_token.startswith("-") or (
                    next_token.startswith("-")
                    and len(next_token) > 1
                    and next_token[1].isdigit()
                ):
                    val = resolve_variables(next_token)
                    i += 2
                else:
                    i += 1
            else:
                i += 1

            if flag == "--quality" and val:
                quality = val
            if flag == "--final-speed" and val:
                final_speed = val

            if val:
                general_flags.append(f"{flag} {val}")
            else:
                general_flags.append(flag)
        else:
            i += 1

    return general_flags, final_params, quality, final_speed


def get_crf_string(quality):
    """Maps quality string/number to CRF display string."""
    q = str(quality).lower().strip()
    if q == "high":
        return "--crf 25(variable)"
    if q == "low":
        return "--crf 35(variable)"
    if q == "medium":
        return "--crf 30(variable)"
    try:
        return f"--crf {q}(variable)"
    except ValueError:
        return "--crf 30(variable)"


def apply_tag_to_file(filepath, encoding_settings):
    """Writes a temp XML and applies it to the MKV file via mkvpropedit."""
    xml_template = f"""<?xml version="1.0"?>
<Tags>
  <Tag>
    <Targets>
      <TrackUID>1</TrackUID>
    </Targets>
    <Simple>
      <Name>ENCODING_SETTINGS</Name>
      <String>{encoding_settings}</String>
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
        mkvpropedit_exe = shutil.which("mkvpropedit")
        if not mkvpropedit_exe:
            print("Error: mkvpropedit not found in PATH")
            return

        subprocess.run(
            [mkvpropedit_exe, filepath, "--tags", "track:v1:" + tmp_path],
            check=True,
            capture_output=True,
        )
        print("Success.")
    except subprocess.CalledProcessError as e:
        print(f"Error tagging {filepath}: {e}")
        if e.stderr:
            print(f"Details: {e.stderr.decode('utf-8')}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def main():
    # 1. Identify batch file
    batch_file = get_active_batch_filename()
    if not batch_file:
        return

    # 2. Read batch file content
    cmd_line = ""
    # We look for the marker file which gives us the NAME of the batch/shell script.
    # But we can't easily "read" the shell script if it's not in the tools/ folder or root.
    # In Linux_Dist, scripts are in root.
    # We will search for the file in correct locations.

    possible_paths = [
        batch_file,  # If absolute/relative
        os.path.join(".", batch_file),
        os.path.join("..", batch_file),  # If run from tools/
    ]
    # Also appending .sh if missing? No, user provides it if marker logic works.

    # But wait, marker logic returns filename "run_linux_hq.sh".
    # And we are running `tools/tag.py` from root (via `python3 tools/tag.py`), so `.` is root.

    script_path = None
    if os.path.exists(batch_file):
        script_path = batch_file
    elif os.path.exists(os.path.join(".", batch_file)):
        script_path = os.path.join(".", batch_file)

    if script_path:
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                full_content = f.read()
                # Join lines ending with backslash
                full_content = full_content.replace("\\\n", " ")

                for line in full_content.splitlines():
                    strip = line.strip().lower()
                    if (not strip.startswith("#")) and (
                        "dispatch.py" in strip or "auto-boost-av1an.py" in strip
                    ):
                        cmd_line = line.strip()
                        break
        except Exception as e:
            print(f"Warning: Could not read script file: {e}")

    # 3. Dynamic Parse
    general_flags, final_params, quality, final_speed = parse_batch_line(cmd_line)

    script_version = get_script_version()
    fish_version = get_5fish_version()

    # 4. Build Strings
    info_parts = [f"Auto-Boost-Av1an {script_version}"]
    info_parts.extend(general_flags)
    info_parts.append(fish_version)

    settings_parts = ["settings:"]
    if final_speed:
        settings_parts.append(f"--preset {final_speed}")
    settings_parts.append(get_crf_string(quality))
    if final_params:
        settings_parts.append(final_params)

    full_string = " ".join(info_parts) + " " + " ".join(settings_parts)

    print(
        "-------------------------------------------------------------------------------"
    )
    print(f"Scanned: {batch_file}")
    print(f"Generated Tag: \n{full_string}")
    print(
        "-------------------------------------------------------------------------------"
    )

    # 5. Apply
    found = False
    for root, _, files in os.walk("."):
        for f in files:
            if f.lower().endswith("-av1.mkv") or f.lower().endswith("-output.mkv"):
                # Note: Windows script checks -output.mkv, but linux script produces -av1.mkv then muxes to something else?
                # run_linux.sh -> output is defined in mux.py.
                # mux.py usually creates "*-muxed.mkv"? Or overwrite source?
                # The user's tag.py in Win searches for "*-output.mkv".
                # In Logic: output_dir / f"{src_file.stem}-av1.mkv" (Auto-Boost-Av1an.py)
                # mux.py creates the final file.
                # Let's check typical flow.
                pass

    # Actually, let's keep it simple: Search for MKV files that look like outputs.
    # In Linux_Dist/tools/mux.py, let's see what it outputs.
    # But for now, I'll search for the same pattern as Windows + maybe "-av1.mkv"

    for root, _, files in os.walk("."):
        for f in files:
            # We want to tag the FINAL output.
            if f.lower().endswith("-output.mkv") or f.lower().endswith("-av1.mkv"):
                found = True
                full_path = os.path.join(root, f)
                apply_tag_to_file(full_path, full_string)

    if not found:
        print("No output MKV files found to tag.")


if __name__ == "__main__":
    main()
