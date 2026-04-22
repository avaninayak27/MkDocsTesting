#!/usr/bin/env python3
##########################################################################
# Copyright [2025] [InnoPhase IoT Inc.]
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##########################################################################

import sys
import subprocess
from pathlib import Path

def run_silent(cmd, cwd=None):
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
        # Print relevant output patterns
        for line in result.stdout.split('\n'):
            if (line.startswith("Created ") or
                line.startswith("Cogging ") or
                "(changed)" in line):
                print(line)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

def format_files_from_list(file_list_path):
    with open(file_list_path, 'r') as f:
        files = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith('#')
        ]

    for filepath in files:
        path = Path(filepath)
        if path.suffix in ['.h'] and path.is_file():  # Only include header files
            subprocess.run(
                ['clang-format', '-i', filepath],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        elif path.suffix in ['.h'] and not path.is_file():
            print(f"Warning: File not found: {filepath}")


def main():
    # Get TOP directory (from argument or auto-detect)
    top_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent.parent
    script_dir = top_dir / "scripts" / "hio"
    middleware_dir = top_dir / "middleware" / "hio"

    print("\nRunning Python processing...")

    # Run Python scripts
    scripts = ["hio_config.py", "generate_hio_files.py", "coggfile.py"]
    for script in scripts:
        run_silent(["python3", "-B", script], cwd=script_dir)

    print("\nRunning cog processing...")
    run_silent(
        ["cog", "-I", str(top_dir/"scripts"), "-r", "@./cogg/cogfiles.txt"],
        cwd=middleware_dir
    )

    print("\n✓ All processing completed successfully")

    print("\nRunning 'clang-format' for generated or modified cogg header files...")
    # Run clang-format for all the files listed in cogfiles.txt
    cog_file_dir = middleware_dir / "cogg/cogfiles.txt"
    format_files_from_list(cog_file_dir)
    print("\n✓ Clang formatting completed successfully")

if __name__ == "__main__":
    main()
