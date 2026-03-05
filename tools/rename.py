import os
import sys

def clean_filename(filename):
    # Split filename and extension
    name, ext = os.path.splitext(filename)
    
    # 1. Remove specific characters: ( ) [ ] !
    for char in "()[]!":
        name = name.replace(char, "")
    
    # 2. Replace spaces with periods
    name = name.replace(" ", ".")
    
    # 3. Append -source if it's not already there
    # (This check prevents adding it twice if you re-run the script)
    if not name.endswith("-source"):
        name += "-source"
        
    return name + ext

def main():
    # Iterate over all files in the current working directory
    for filename in os.listdir('.'):
        # Process only .mkv files
        if filename.lower().endswith(".mkv"):
            
            # Skip files that already have -source at the end to prevent double-processing
            # (Matches logic of the original batch file, but does it per-file)
            if filename.endswith("-source.mkv"):
                continue

            new_name = clean_filename(filename)
            
            # Only rename if the name has actually changed
            if new_name != filename:
                try:
                    os.rename(filename, new_name)
                    print(f"Renamed: '{filename}' -> '{new_name}'")
                except OSError as e:
                    print(f"Error renaming '{filename}': {e}")

if __name__ == "__main__":
    main()