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
import json
from pathlib import Path

def read_copyright_notice(script_dir):
    """Read copyright notice from copyright_notice.txt file and format it properly"""
    copyright_path = script_dir / "copyright_notice.txt"
    try:
        with open(copyright_path, 'r') as f:
            copyright_lines = f.read().splitlines()

        # Format as C-style comment with proper asterisks
        formatted_lines = ["/*"]
        for line in copyright_lines:
            if line.strip() == "":
                formatted_lines.append(" *")
            else:
                formatted_lines.append(f" * {line}")
        formatted_lines.append(" */")

        # Join with newlines and add one empty line after
        return "\n".join(formatted_lines) + "\n\n"
    except FileNotFoundError:
        print(f"Warning: Could not find copyright notice file at {copyright_path}")
        return "/* Copyright notice not found */\n"

def get_filename_prefix(module_name):
    """Determine the filename prefix based on module name"""
    if module_name in ['sys', 'debug']:
        return 'inph_hio_'
    return 'hio_'

def create_file_content(script_dir, module_name, is_header):
    """Generate file content with copyright, doxygen (for headers only), and the relevant cog section"""
    # Get copyright header from external file (already formatted with trailing newline)
    copyright_header = read_copyright_notice(script_dir)

    # Doxygen section (only for header files)
    doxygen_section = ""
    if is_header:
        doxygen_section = f"""/*
[[[cog
import cog, generate
generate.doxygen(generate.Emitter(cog.out), '{module_name}')
]]] */

/* [[[end]]] */
"""

    # Module-specific cog section
    module_section = f"""/*
[[[cog
import cog, generate
generate.{'header' if is_header else 'api'}(generate.Emitter(cog.out), '{module_name}')
]]] */

/* [[[end]]] */
"""

    # Combine sections with appropriate spacing
    content = copyright_header
    if is_header:
        content += f"{doxygen_section}\n"
    content += module_section

    return content

def clean_path(path_str):
    """Remove leading 'apu/' from path if present"""
    if path_str.startswith('apu/'):
        return path_str[4:]
    return path_str

def generate_files(script_dir, config_path, apu_top_dir):
    """Generate .h and .c files based on configuration"""
    # Read the configuration file
    with open(config_path, 'r') as f:
        config = json.load(f)

    for module_name, module_config in config.items():
        if not module_config.get('enable', False):
            continue

        # Determine filename prefix
        prefix = get_filename_prefix(module_name)

        # Get and clean paths from config
        header_path = clean_path(module_config['header_file_path'])
        source_path = clean_path(module_config['c_file_path'])

        # Create header file if it doesn't exist
        h_path = apu_top_dir / header_path / f"{prefix}{module_name}.h"
        h_path.parent.mkdir(parents=True, exist_ok=True)

        if not h_path.exists():
            with open(h_path, 'w') as f:
                f.write(create_file_content(script_dir, module_name, is_header=True))
            print(f"Created header file: {h_path}")

        # Create source file if it doesn't exist
        c_path = apu_top_dir / source_path / f"{prefix}{module_name}.c"
        c_path.parent.mkdir(parents=True, exist_ok=True)

        if not c_path.exists():
            with open(c_path, 'w') as f:
                f.write(create_file_content(script_dir, module_name, is_header=False))
            print(f"Created source file: {c_path}")

if __name__ == "__main__":
    # Get absolute path to APU top directory
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    apu_top_dir = script_dir.parent.parent

    # Config path is in same directory as script
    config_path = script_dir / "hio_config.json"

    # Verify APU top directory exists
    if not apu_top_dir.exists():
        print(f"Error: Could not find APU top directory at {apu_top_dir}")
        print("Please ensure script is run from correct location (apu/scripts/hio/)")
        exit(1)

    generate_files(script_dir, config_path, apu_top_dir)
