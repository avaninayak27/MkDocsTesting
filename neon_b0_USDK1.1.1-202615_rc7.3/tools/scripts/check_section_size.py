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

import argparse
import sys
from elftools.elf.elffile import ELFFile

def get_section_size(elffile, section_name):
    """
    Retrieve the size of a given section from the ELF file.
    """
    with open(elffile, 'rb') as file:
        elf = ELFFile(file)
        section = elf.get_section_by_name(section_name)
        if not section:
            print(f"Error: Section '{section_name}' not found in {elffile}")
            sys.exit(1)
        return section.header['sh_size']

def main():
    # Argument parsing
    parser = argparse.ArgumentParser(description="Check ELF section size")
    parser.add_argument("--elffile", required=True, help="Path to the ELF file")
    parser.add_argument("--section", required=True, help="Section name to check")
    parser.add_argument("--max_section_size", required=True, type=int, help="Maximum allowed size of the section")
    args = parser.parse_args()

    # Fetch the section size
    try:
        section_size = get_section_size(args.elffile, args.section)
    except Exception as e:
        print(f"Error reading ELF file: {e}")
        sys.exit(1)

    # Compare with the maximum allowed size
    print(f"Section '{args.section}' size: {section_size} bytes")
    if section_size > args.max_section_size:
        print(f"Error: Section '{args.section}' exceeds the max allowed size of {args.max_section_size} bytes!")
        sys.exit(1)

    print("Section size is within the allowed limit.")
    sys.exit(0)

if __name__ == "__main__":
    main()
