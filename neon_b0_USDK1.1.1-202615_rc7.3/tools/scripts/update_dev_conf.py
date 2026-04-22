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

import json, shutil, sys, os
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection

def hex_to_string_list(hex_string: str):
    # Convert hex string to bytes
    binary_blob = bytes.fromhex(hex_string)
    # Split by null byte (\x00) and decode each part
    return [s.decode('utf-8') for s in binary_blob.split(b'\x00') if s]

def get_symbol_info(elf_path, symbol_name):
    with open(elf_path, 'rb') as f:
        elf = ELFFile(f)

        for section in elf.iter_sections():
            if isinstance(section, SymbolTableSection):
                for symbol in section.iter_symbols():
                    if symbol.name == symbol_name:
                        addr = symbol['st_value']
                        size = symbol['st_size']
                        print(f"Symbol '{symbol_name}' found at address 0x{addr:X}, size {size} bytes")
                        return addr, size

    print(f"Symbol '{symbol_name}' not found.")
    return None, None

def get_file_offset(elf_path, symbol_addr):
    with open(elf_path, 'rb') as f:
        elf = ELFFile(f)

        for segment in elf.iter_segments():
            seg_start = segment['p_vaddr']
            seg_end = seg_start + segment['p_memsz']

            if seg_start <= symbol_addr < seg_end:
                file_offset = segment['p_offset'] + (symbol_addr - seg_start)
                return int(file_offset)

    return None

def get_file_offset_and_padded_data(elf_path, symbol_name, new_data_bytes):
    try:
        symbol_addr, max_size = get_symbol_info(elf_path, symbol_name)
        if symbol_addr is None:
            print(f"Error: {symbol_name} symbol not found.")
            raise Exception(f"Error: {symbol_name} symbol not found.")

        if len(new_data_bytes) > max_size:
            print(f"Error: new data ({len(new_data_bytes)} bytes) exceeds max size ({max_size} bytes) of '{symbol_name}'.")
            raise Exception(f"Error: new data ({len(new_data_bytes)} bytes) exceeds max size ({max_size} bytes) of '{symbol_name}'.")

        file_offset = get_file_offset(elf_path, symbol_addr)
        if file_offset is None:
            print(f"Error: {symbol_name} could not determine file offset.")
            raise Exception(f"Error: {symbol_name} could not determine file offset.")

        # Pad with nulls if shorter than allocated space
        padded_data = new_data_bytes.ljust(max_size, b'\x00')
        return file_offset, padded_data
    
    except Exception as e:
        raise Exception(str(e))

def get_bootargs_blob(json_data): #REMOVE FOR IFX BUILD
    # Extract and remove "bootargs" if present #REMOVE FOR IFX BUILD
    bootargs_kv_list = [] #REMOVE FOR IFX BUILD
    if "bootargs" in json_data: #REMOVE FOR IFX BUILD
        bootargs = json_data.pop("bootargs") #REMOVE FOR IFX BUILD
        if isinstance(bootargs, dict): #REMOVE FOR IFX BUILD
            bootargs_kv_list = [f"{k}={v}" for k, v in bootargs.items()] #REMOVE FOR IFX BUILD
        else: #REMOVE FOR IFX BUILD
            raise ValueError("'bootargs' is not a dictionary") #REMOVE FOR IFX BUILD
        print("bootargs data", bootargs_kv_list) #REMOVE FOR IFX BUILD
    bootarg_blob = b'' #REMOVE FOR IFX BUILD
    if bootargs_kv_list: #REMOVE FOR IFX BUILD
        bootarg_blob = b'\x00'.join(arg.encode('ascii') for arg in bootargs_kv_list) + b'\x00' #REMOVE FOR IFX BUILD
    return json_data, bootarg_blob #REMOVE FOR IFX BUILD

def main(json_file, elf_file):
    
    config_symbol="dev_cfg_array"
    bootarg_symbol="npu_bootargs" #REMOVE FOR IFX BUILD
    try:
        try:
            with open(json_file, 'r') as f:
                json_data = json.load(f)
        except Exception as e:
            raise Exception("JSON format issue on " + json_file + " - "  + str(e))

        new_elf_file = elf_file[:-4] + "_mod.elf"
        shutil.copyfile(elf_file, new_elf_file)
        elf_file = new_elf_file

        json_data, bootarg_blob = get_bootargs_blob(json_data) #REMOVE FOR IFX BUILD
                        #REMOVE FOR IFX BUILD
        print("dev_config data", json_data)
        json_blob = json.dumps(json_data).encode('utf-8') + b'\x00'

        with open(elf_file, 'r+b') as f:
            if bootarg_blob: #REMOVE FOR IFX BUILD
                #get offset and padded data for the bootarg #REMOVE FOR IFX BUILD
                bootarg_offset, bootarg_bdata = get_file_offset_and_padded_data(elf_file, bootarg_symbol, bootarg_blob) #REMOVE FOR IFX BUILD
                f.seek(bootarg_offset) #REMOVE FOR IFX BUILD
                f.write(bootarg_bdata) #REMOVE FOR IFX BUILD
                # print(f"Replaced '{bootarg_symbol}' with JSON content ({len(bootarg_bdata)} bytes).") #REMOVE FOR IFX BUILD
            #get offset and padded data for the config data
            cfg_offset, cfg_bdata = get_file_offset_and_padded_data(elf_file, config_symbol, json_blob)
            f.seek(cfg_offset)
            f.write(cfg_bdata)
            # print(f"Replaced '{config_symbol}' with JSON content ({len(cfg_bdata)} bytes).")
            return elf_file

        pass
    except Exception as e:
        try:
            if "mod.elf" in elf_file:
                os.remove(elf_file)
        except:
            pass
        raise Exception(str(e))

if __name__ == "__main__":

    DEFAULT_JSON = "./dev_config.json"
    DEFAULT_ELF  = "./test_dev_cfg.elf"

    # Help option
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("Usage:")
        print("  python update_dev_conf.py                      # use default files")
        print("  python update_dev_conf.py config.json image.elf # provide both files")
        sys.exit(0)

    # Argument validation
    if len(sys.argv) == 1:
        # No args → defaults
        json_file = DEFAULT_JSON
        elf_file = DEFAULT_ELF

    elif len(sys.argv) == 3:
        # Two args → user-specified
        json_file = sys.argv[1]
        elf_file = sys.argv[2]

    else:
        print("Error: You must provide either ZERO arguments or EXACTLY TWO arguments.")
        print("Run with --help for usage instructions.")
        sys.exit(1)

    # Run main
    try:
        out_elf = main(json_file, elf_file)
        print(f"Patched ELF saved as: {out_elf}")
    except Exception as e:
        print("Exception occurred:", str(e))
        sys.exit(1)


    


