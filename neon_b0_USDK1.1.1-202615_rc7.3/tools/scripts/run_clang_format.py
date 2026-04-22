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

import subprocess
from pathlib import Path
import sys

def run_clang_format(root_dir="."):
    # Recursively find all .c and .h files
    files = list(Path(root_dir).rglob("*.c")) + list(Path(root_dir).rglob("*.h"))
    
    if not files:
        print("No .c or .h files found.")
        return

    for file in files:
        print(f"Formatting {file}")
        subprocess.run(["clang-format", "-i", "-style=file", str(file)], check=True)

if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    run_clang_format(root)
