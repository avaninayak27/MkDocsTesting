#!/bin/bash

set -e  # Exit immediately on error
#set -x  # Enable verbose debugging

elf_file="$1"

# Check if command line argument is empty or not present
if [ -z "$elf_file" ] || [ ! -f "$elf_file" ]; then
    echo "Please specify a valid ELF file name..."
    exit 1
fi

echo $elf_file
echo "" > data.txt

# Generate library size data
python3 scripts/check_lib_size_in_elf.py $elf_file --lib libfreertos.a | tail -n 3 >> data.txt
python3 scripts/check_lib_size_in_elf.py $elf_file --lib libosal.a     | tail -n 3 >> data.txt
python3 scripts/check_lib_size_in_elf.py $elf_file --lib libpdl.a      | tail -n 3 >> data.txt
python3 scripts/check_lib_size_in_elf.py $elf_file --lib libhal.a      | tail -n 3 >> data.txt
python3 scripts/check_lib_size_in_elf.py $elf_file --lib libplatform.a | tail -n 3 >> data.txt
python3 scripts/check_lib_size_in_elf.py $elf_file --lib libiwm.a      | tail -n 3 >> data.txt
python3 scripts/check_lib_size_in_elf.py $elf_file --lib libjansson.a  | tail -n 3 >> data.txt

# Print the data for debugging
#echo "Generated data.txt content:"
#cat data.txt

# Run the embedded Python script
python3 - <<'EOF_PYTHON'
import re

def parse_library_data(file_path):
    """Parse the library data from the file."""
    libraries = []
    with open(file_path, 'r') as file:
        content = file.read()

        # Regex to match library blocks
        pattern = r"Library: (\S+)\s+Current code size: (\d+) bytes\.\s+Current total data size \(Data \+ BSS\): (\d+) bytes\."
        matches = re.findall(pattern, content)

        for match in matches:
            lib_name, code_size, data_size = match
            libraries.append((lib_name, int(code_size), int(data_size)))

    return libraries

def display_table(libraries):
    """Display the library data in a table format with full boundaries."""
    if not libraries:
        print("No valid library data found in data.txt. Ensure the input ELF file and script outputs are correct.")
        exit(1)

    # Define column headers
    headers = ["Library Name", "Code Size (bytes)", "Data Size (bytes)"]
    column_widths = [max(len(headers[0]), max(len(lib[0]) for lib in libraries)),
                     max(len(headers[1]), max(len(str(lib[1])) for lib in libraries)),
                     max(len(headers[2]), max(len(str(lib[2])) for lib in libraries))]

    # Print the table
    total_width = sum(column_widths) + len(column_widths) * 3 + 1
    print("+" + "-" * (total_width - 2) + "+")
    print("| " + f"{headers[0]:<{column_widths[0]}}" + " | " +
          f"{headers[1]:<{column_widths[1]}}" + " | " +
          f"{headers[2]:<{column_widths[2]}}" + " |")
    print("+" + "+".join("-" * (w + 2) for w in column_widths) + "+")

    for lib in libraries:
        print("| " + f"{lib[0]:<{column_widths[0]}}" + " | " +
              f"{lib[1]:<{column_widths[1]}}" + " | " +
              f"{lib[2]:<{column_widths[2]}}" + " |")
        print("+" + "+".join("-" * (w + 2) for w in column_widths) + "+")

# Parse the data file and display the table
libraries = parse_library_data("data.txt")
display_table(libraries)
EOF_PYTHON

# Clean up
rm -f data.txt
