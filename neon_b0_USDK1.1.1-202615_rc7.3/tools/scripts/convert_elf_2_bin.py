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

from elftools.elf.elffile import ELFFile
from pathlib import Path
import argparse, os

def is_valid_segment(seg):
    # Only include loadable segments with data (not NOBITS) and alloc flag
    hdr = seg.header
    # p_type should be PT_LOAD
    if hdr.p_type != 'PT_LOAD' and hdr['p_type'] != seg['p_type']:
        return False
    # seg.data() gives data for file-backed segments; NOBITS will give size zero
    size = seg.header.p_filesz
    if size == 0:
        return False
    # Check flags: ensure "ALLOC" bit is set in p_flags (value & PF_ALLOC)
    PF_ALLOC = 0x4  # on many systems, but confirm your system
    if not (hdr.p_flags & PF_ALLOC):
        return False
    return True

def combine_bins(inputs, output_bin):
    from intelhex import IntelHex

    # Define input binaries and where to place them
    # inputs = [
    #     ("tfm_s.bin", 0x000000),
    #     ("hello_world.bin", 0x400000),
    # ]

    ih = IntelHex()

    # Load each binary at the specified offset
    for filename, offset in inputs:
        print("combine bin:", filename, "offset", hex(offset))
        with open(filename, "rb") as f:
            data = f.read()
            ih.puts(offset, data)

    # Write to final output binary
    ih.padding = 0x00 #0xFF
    ih.tobinfile(output_bin)
    print(f"tfm combine bin {output_bin}")

def elf_to_bin(elf_path: str, bin_path: str, tfm_app = "", ns_app_image_offset = 0x400000):
    if tfm_app:
        elfs = [tfm_app, elf_path]
        bins = []
        for each_elf in elfs:
            if each_elf[-4:] == ".elf":
                each_bin = each_elf[:-4] + ".bin"
                convert_to_bin(each_elf, each_bin)
            else:
                each_bin = each_elf
            bins.append(each_bin)
        
        inputs = [
        (bins[0], 0x000000),
        (bins[1], ns_app_image_offset),
        ]

        combine_bins(inputs, bin_path)
        for i in range(2):
            try:
                if elfs[i] != bins[i]:
                    os.remove(bins[i])
            except:
                pass

    else:
        convert_to_bin(elf_path, bin_path)

def find_skip_offset(elf):
    """
    Objcopy removes everything before the first SHF_ALLOC section.
    Compute minimum section offset of all ALLOC sections.
    """
    min_off = None
    for sec in elf.iter_sections():
        if sec['sh_flags'] & 0x2:  # SHF_ALLOC
            off = sec['sh_offset']
            if min_off is None or off < min_off:
                min_off = off
    return min_off if min_off else 0

def convert_to_bin(elf_path: str, bin_path: str, debug = False):
    with open(elf_path, 'rb') as f:
        elf = ELFFile(f)
        
        load_segments = []
        for seg in elf.iter_segments():
            if seg['p_type'] == 'PT_LOAD' or seg['p_type'] == 'PT_ARM_EXIDX':
                load_segments.append(seg)
                if debug:
                    print("Included: ", seg.header)
            else:
                if debug:
                    print("Ignore: ", seg.header)

        if not load_segments:
            raise RuntimeError("No LOAD segments found.")

        # Objcopy behavior → use virtual address when physAddr is "weird"
        base = min(seg['p_paddr'] for seg in load_segments)
        end  = max(seg['p_paddr'] + seg['p_filesz'] for seg in load_segments if seg['p_filesz'] !=0) #p_memsz

        total_size = end - base
        if debug:
            print(f"Base VA: 0x{base:X}")
            print(f"End VA : 0x{end:X}")
            print(f"Total size: 0x{total_size:X} bytes")

        image = bytearray(total_size)
        max_size = 0
        for seg in load_segments:
            data = seg.data()
            offset = seg['p_paddr'] - base
            image[offset:offset + len(data)] = data
            if max_size < offset + len(data):
                max_size = offset + len(data)

            if debug:
                print(f"'p_type': {seg['p_type']}, 'p_offset': 0x{seg['p_offset']:X}, 'p_vaddr': 0x{seg['p_vaddr']:X}, 'p_paddr': 0x{seg['p_paddr']:X}, 'p_filesz': 0x{seg['p_filesz']:X}, 'p_memsz': 0x{seg['p_memsz']:X}, 'p_flags': {seg['p_flags']}, 'p_align': 0x{seg['p_align']:X}")
                print(f"LOAD @ VA 0x{seg['p_vaddr']:X}, PA 0x{seg['p_paddr']:X},"
                      f"filesz={seg['p_filesz']}, memsz={seg['p_memsz']} "
                      f"-> offset={offset}, {seg['p_type']}")

        # --- Detect ELF header and skip ---
        ELF_MAGIC = b"\x7FELF"

        if image.startswith(ELF_MAGIC):
            STRIP_SIZE = find_skip_offset(elf)
            if len(image) > STRIP_SIZE:
                image = image[STRIP_SIZE:]
            else:
                raise RuntimeError("Image smaller than 0x1000, cannot strip ELF header.")
        else:
            if debug:
                print("No ELF header detected → writing full image")

        with open(bin_path, 'wb') as f2:
            f2.write(image)

        if debug:
            print(f"Created {bin_path} (max_size:0x{max_size:X}(0x{len(image):X} bytes)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert ELF to BIN")
    parser.add_argument("inp_elf", help="Path to input ELF file")
    parser.add_argument("-o", "--out", help="Optional output BIN file path")

    args = parser.parse_args()

    inp_elf = Path(args.inp_elf)
    
    if args.out:
        out_bin = Path(args.out)
    else:
        out_bin = inp_elf.with_suffix(".bin")  # Replace .elf with .bin

    elf_to_bin(str(inp_elf), str(out_bin))

