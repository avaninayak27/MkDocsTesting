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
import shutil
import subprocess
import sys

with open('middleware/external/submodules.json', 'r') as file:
    data = json.load(file)

for item in data:
    repo_url = item['url']
    tag = item['tag']
    location = item['location']

    if os.path.exists(location) and os.path.isdir(os.path.join(location, '.git')):
        # Check if current tag matches expected tag
        try:
            result = subprocess.run(
                ['git', 'describe', '--tags', '--exact-match'],
                cwd=location, capture_output=True, text=True
            )
            current_tag = result.stdout.strip()

            if current_tag == tag:
                print(f"[OK] {location} is already at tag: {tag}")
                continue  # Skip to next item
            else:
                print(f"[ERROR] {location} has tag {current_tag}, expected {tag}")
                sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Failed to check tag in {location}: {e}")
            sys.exit(1)
    else:
        if os.path.exists(location):
            print(f"[WARN] {location} exists but is not a git repo. Removing it...")
            shutil.rmtree(location)  # Dangerous if misused, use carefully!

        # Clone and checkout if directory does not exist
        os.makedirs(location, exist_ok=True)
        print(f"[INFO] Cloning {repo_url} into {location}")
        subprocess.run(['git', 'clone', repo_url, location], check=True)
        subprocess.run(['git', 'checkout', tag], cwd=location, check=True)
        parent_dir = os.path.dirname(location)
        print(f"[DONE] Cloned {repo_url} to {location}, checked out {tag}")
