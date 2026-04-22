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
##########################################################################s

import json
import os
import fnmatch

# Define constants for the paths
TOP = os.path.abspath("../..")  # Ensure TOP is an absolute path
HIO_INC_API_DIR = os.path.join(TOP, "middleware/hio/inc/api")
HIO_SRC_API_DIR = os.path.join(TOP, "middleware/hio/src/api")
MIDDLEWARE_HIO_COGG_DIR = os.path.join(TOP, "middleware/hio/cogg")
COGG_FILE_PATH = os.path.join(MIDDLEWARE_HIO_COGG_DIR, "cogfiles.txt")

# Path to the JSON file (in the same directory as the script)
JSON_FILE_PATH = os.path.join(os.path.dirname(__file__), "hio_config.json")

def generate_file_paths(module_name):
    """Generate the file paths for .h and .c files based on the module name."""
    pattern = f"*{module_name}.*"
    h_file, c_file = None, None

    # Search for .h files in HIO_INC_API_DIR
    for file in os.listdir(HIO_INC_API_DIR):
        if fnmatch.fnmatch(file, pattern) and file.endswith('.h'):
            h_file = os.path.join(HIO_INC_API_DIR, file)
            break

    # Search for .c files in HIO_SRC_API_DIR
    for file in os.listdir(HIO_SRC_API_DIR):
        if fnmatch.fnmatch(file, pattern) and file.endswith('.c'):
            c_file = os.path.join(HIO_SRC_API_DIR, file)
            break

    return h_file, c_file

def process_json_file(json_file):
    """Process the JSON file and write the file paths into cogfiles.txt."""
    if not os.path.exists(json_file):
        print(f"Error: JSON file '{json_file}' does not exist.")
        return

    with open(json_file, 'r') as f:
        data = json.load(f)

    # Ensure the cogfiles.txt directory exists
    os.makedirs(MIDDLEWARE_HIO_COGG_DIR, exist_ok=True)

    with open(COGG_FILE_PATH, 'w') as cogg_file:
        for module_name, config in data.items():
            # Only process enabled modules
            if config.get('enable', False):
                h_file, c_file = generate_file_paths(module_name)

                if h_file and c_file:
                    hio_relative_h_file = os.path.relpath(h_file, os.path.join(TOP, "middleware/hio"))
                    hio_relative_c_file = os.path.relpath(c_file, os.path.join(TOP, "middleware/hio"))
                    cogg_file.write(f"./{hio_relative_h_file}\n")
                    cogg_file.write(f"./{hio_relative_c_file}\n")
                else:
                    print(f"Warning: Could not find .h or .c files for module '{module_name}'")

if __name__ == "__main__":
    # Process the JSON file
    process_json_file(JSON_FILE_PATH)
