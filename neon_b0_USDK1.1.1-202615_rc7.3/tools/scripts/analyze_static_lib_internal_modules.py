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

def analyze_files_with_threshold(library_path, file_list=None, max_data=None, max_text=None):
    if not os.path.exists(library_path):
        print(f"Error: File '{library_path}' does not exist.")
        sys.exit(1) # Exit with failure
        return

    try:
        # Run 'arm-none-eabi-size -t' command
        size_output = subprocess.check_output(['arm-none-eabi-size', '-t', library_path], text=True)

        # Print the output for reference
        print(size_output)

        # Parse the file_list into a set
        target_files = set(file_list.split(",")) if file_list else None
        print(f"Target files: {target_files}")

        # Extract filenames from the size_output
        tool_output_filenames = set()
        lines = size_output.splitlines()[1:]  # Skip the header line

        section_indices = {"text": 0, "data": 1, "bss": 2, "filename": 5}
        
        for line in lines:
            columns = line.split()
            if len(columns) < 6:
                continue  # Skip malformed lines
            filename = os.path.basename(columns[section_indices["filename"]]).strip().lower()
            tool_output_filenames.add(filename)

        # Check if each target file exists in the tool output
        if target_files:
            for target_file in target_files:
                if target_file.lower() not in tool_output_filenames:
                    raise ValueError(f"Error: '{target_file}' is not found in the tool output list.")

        # Extract data by parsing each line except the header and TOTALS
        total_text = 0
        total_data = 0

        for line in lines:
            columns = line.split()
            if len(columns) < 6:
                continue  # Skip malformed lines

            filename = os.path.basename(columns[section_indices["filename"]]).strip().lower()  # Normalize filename to base name

            if target_files is None or filename in target_files:
                text_size = int(columns[section_indices["text"]])
                data_size = int(columns[section_indices["data"]])
                bss_size = int(columns[section_indices["bss"]])

                total_text += text_size
                total_data += data_size + bss_size

        print(f"Sum of text sizes for selected files: {total_text} bytes")
        print(f"Sum of data+bss sizes for selected files: {total_data} bytes")

        if max_text is not None and total_text > max_text:
            raise ValueError(f"Error: Total text size ({total_text} bytes) exceeds the maximum allowed ({max_text} bytes).")

        if max_data is not None and total_data > max_data:
            raise ValueError(f"Error: Total data+bss size ({total_data} bytes) exceeds the maximum allowed ({max_data} bytes).")

        print("All checks passed.")

    except subprocess.CalledProcessError as e:
        print(f"Error running subprocess: {e}")
        sys.exit(1) # Exit with failure
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1) # Exit with failure

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze a static library and check section sizes for specific files.")
    parser.add_argument("library_path", help="Path to the static library")
    parser.add_argument("--file_list", type=str, help="Comma-separated list of .o filenames to analyze")
    parser.add_argument("--max_data", type=int, help="Maximum allowed size for the .data+bss sections")
    parser.add_argument("--max_text", type=int, help="Maximum allowed size for the .text section")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    analyze_files_with_threshold(args.library_path, file_list=args.file_list, max_data=args.max_data, max_text=args.max_text)
    sys.exit(0) # Exit with success
