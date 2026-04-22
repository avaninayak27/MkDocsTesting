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

def read_copyright_notice():
    """Read and format the copyright notice for Python files"""
    try:
        with open('copyright_notice.txt', 'r') as f:
            notice = f.read().strip()
            # Convert to Python comment format
            return "\n".join(f"# {line}" if line.strip() else "#"
                           for line in notice.split('\n'))
    except FileNotFoundError:
        raise SystemExit("Error: copyright_notice.txt not found")

def generate_init_content(modules, notice):
    """Generate content for __init__.py files"""
    content = [notice, "\n__all__ = ["]
    content.append('    "base",')
    content.extend(f'    "{module}",' for module in modules)
    content.append("]")
    return "\n".join(content)

def main():
    # Read and format copyright notice
    copyright_notice = read_copyright_notice()

    # Read configuration
    try:
        with open('hio_config.json') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise SystemExit("Error: hio_config.json not found")

    # Get enabled modules
    enabled_modules = [module for module, details in data.items()
                     if details.get("enable", False)]

    # Generate and write files
    with open("__init__.py", "w") as f:
        f.write(generate_init_content(enabled_modules, copyright_notice))

    with open("__init_sdk__.py", "w") as f:
        f.write(generate_init_content(enabled_modules, copyright_notice))

if __name__ == "__main__":
    main()
