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

import json
import os
import subprocess
import configparser
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Generate JSON of submodule info with exclusions")
parser.add_argument('--exclude', action='append', help="Exclude submodules by name", default=[])
args = parser.parse_args()

# Initialize configparser to read .gitmodules
config = configparser.ConfigParser()
config.read('.gitmodules')

submodules_info = []

# Process each submodule in .gitmodules
for section in config.sections():
    if section.startswith("submodule"):
        full_path = config[section]["path"]
        url = config[section]["url"]
        location = config[section]["path"]

        # Extract only the last part of the path as the name
        name = os.path.basename(full_path)

        # Skip if the submodule is in the exclude list
        if any(excl in full_path for excl in args.exclude):
            continue

        # Find the checked-out commit in .git/modules/<submodule_path>
        git_dir = os.path.join('.git/modules', location)
        tag = "not initialized"

        if os.path.isdir(git_dir):
            # Try to get the tag for the current commit
            result = subprocess.run(
                ['git', '--git-dir', git_dir, 'describe', '--tags', '--exact-match'],
                capture_output=True, text=True
            )

            # Check if a tag was found; otherwise, fall back to the SHA
            if result.returncode == 0:
                tag = result.stdout.strip()
            else:
                # If no tag, get the SHA instead
                result = subprocess.run(
                    ['git', '--git-dir', git_dir, 'rev-parse', 'HEAD'],
                    capture_output=True, text=True
                )
                tag = result.stdout.strip() if result.returncode == 0 else "unknown"

        # Append submodule details to list
        submodules_info.append({
            "name": name,
            "url": url,
            "tag": tag,
            "location": location
        })

# Write the data to a JSON file
with open('middleware/external/submodules.json', 'w') as json_file:
    json.dump(submodules_info, json_file, indent=4)

print("submodules.json file created successfully.")
