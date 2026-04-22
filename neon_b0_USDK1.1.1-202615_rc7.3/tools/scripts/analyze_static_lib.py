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

import os
import subprocess
import sys

def analyze_static_library_with_threshold(library_path, max_data=None, max_text=None):
    if not os.path.exists(library_path):
        print(f"Error: File '{library_path}' does not exist.")
        sys.exit(1) # Exit with failure
        return

    try:
        # Run 'arm-none-eabi-size -t' command
        size_output = subprocess.check_output(['arm-none-eabi-size', '-t', library_path], text=True)

        # Print the output for reference
        print(size_output)

        # Extract the last line containing totals
        lines = size_output.splitlines()
        if len(lines) < 2:
            raise ValueError("Unexpected output format: Not enough lines.")

        totals_line = lines[-1].split()

        # Map the sections to their respective indices
        section_indices = {"text": 0, "data": 1, "bss": 2}

        if max_text is None and max_data is None:
            print("No thresholds provided. Exiting.")
            return

        # Check text size if max_text is provided
        if max_text is not None:
            text_size = int(totals_line[section_indices["text"]])
            print(f"Total text size: {text_size} bytes")
            if text_size > max_text:
                raise ValueError(f"Error: text size ({text_size} bytes) exceeds the maximum allowed ({max_text} bytes).")

        # Check data size if max_data is provided
        if max_data is not None:
            data_size = int(totals_line[section_indices["data"]])
            print(f"Total data size: {data_size} bytes")
            if data_size > max_data:
                raise ValueError(f"Error: data size ({data_size} bytes) exceeds the maximum allowed ({max_data} bytes).")

        print("All checks passed.")

    except subprocess.CalledProcessError as e:
        print(f"Error running subprocess: {e}")
        sys.exit(1) # Exit with failure
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1) # Exit with failure

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze a static library and check section sizes.")
    parser.add_argument("library_path", help="Path to the static library")
    parser.add_argument("--max_data", type=int, help="Maximum allowed size for the .data section")
    parser.add_argument("--max_text", type=int, help="Maximum allowed size for the .text section")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    analyze_static_library_with_threshold(args.library_path, max_data=args.max_data, max_text=args.max_text)
    sys.exit(0) # Exit with success
