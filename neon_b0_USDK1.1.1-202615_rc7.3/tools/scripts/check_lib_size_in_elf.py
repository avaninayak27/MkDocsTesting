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
import argparse
from elftools.elf.elffile import ELFFile

def get_symbol_value(elf, symbol_name):
    """Retrieve the value of a symbol from the ELF file."""
    for section in elf.iter_sections():
        if not isinstance(section, dict) and section.name == ".symtab":
            for symbol in section.iter_symbols():
                if symbol.name == symbol_name:
                    return symbol.entry.st_value
    raise ValueError(f"Symbol '{symbol_name}' not found in ELF file.")

def check_code_size(start_symbol, end_symbol, max_size, elf):
    """Calculate and optionally verify the code size."""
    start = get_symbol_value(elf, start_symbol)
    end = get_symbol_value(elf, end_symbol)
    size = end - start

    # Print the start and end symbols in hexadecimal
    print(f"Code section: {start_symbol} = {hex(start)}, {end_symbol} = {hex(end)}")
    print(f"Code section size is {size} bytes.")

    if max_size > 0 and size > max_size:
        raise ValueError(f"Code section size ({size} bytes) exceeds limit ({max_size} bytes).")

    return size

def check_data_size(lib_name, max_size, elf):
    """Calculate and optionally verify the total data size (data + BSS)."""
    data_start_symbol = f"__{lib_name}_data_start"
    data_end_symbol = f"__{lib_name}_data_end"
    bss_start_symbol = f"__{lib_name}_bss_start"
    bss_end_symbol = f"__{lib_name}_bss_end"

    # Get data and BSS sizes
    data_start = get_symbol_value(elf, data_start_symbol)
    data_end = get_symbol_value(elf, data_end_symbol)
    bss_start = get_symbol_value(elf, bss_start_symbol)
    bss_end = get_symbol_value(elf, bss_end_symbol)

    # Calculate total size
    data_size = data_end - data_start
    bss_size = bss_end - bss_start
    total_data_size = data_size + bss_size

    # Print the start and end symbols in hexadecimal
    print(f"Data section: {data_start_symbol} = {hex(data_start)}, {data_end_symbol} = {hex(data_end)}")
    print(f"BSS section: {bss_start_symbol} = {hex(bss_start)}, {bss_end_symbol} = {hex(bss_end)}")
    print(f"Total data size (Data + BSS) is {total_data_size} bytes.")

    if max_size > 0 and total_data_size > max_size:
        raise ValueError(f"Total data size ({total_data_size} bytes) exceeds limit ({max_size} bytes).")

    return total_data_size

def main():
    parser = argparse.ArgumentParser(description="Check ELF file sizes for code and data sections.")
    parser.add_argument("elf_file", help="Path to the ELF file.")
    parser.add_argument("--lib", required=True, help="Library name (e.g., libplatform).")
    parser.add_argument("--max_code_size", type=int, default=0, help="Maximum code size in bytes.")
    parser.add_argument("--max_data_size", type=int, default=0, help="Maximum data size in bytes.")
    args = parser.parse_args()

    try:
        with open(args.elf_file, "rb") as elf_file:
            elf = ELFFile(elf_file)

            # Generate the variable names dynamically based on the library name
            lib_name = args.lib.replace(".a", "")  # Remove ".a" if it's present

            # Check and print code size
            code_start_symbol = f"__{lib_name}_code_start"
            code_end_symbol = f"__{lib_name}_code_end"
            code_size = check_code_size(code_start_symbol, code_end_symbol, args.max_code_size, elf)

            # Check and print data size
            data_size = check_data_size(lib_name, args.max_data_size, elf)

            # If no limits are provided, print the current usage
            if args.max_code_size == 0 and args.max_data_size == 0:
                print(f"Library: {args.lib}")
                print(f"Current code size: {code_size} bytes.")
                print(f"Current total data size (Data + BSS): {data_size} bytes.")
    except FileNotFoundError:
        print(f"Error: File '{args.elf_file}' not found.")
        sys.exit(1)  # Exit with failure
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)  # Exit with failure
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)  # Exit with failure

    sys.exit(0)  # Exit successfully

if __name__ == "__main__":
    main()
