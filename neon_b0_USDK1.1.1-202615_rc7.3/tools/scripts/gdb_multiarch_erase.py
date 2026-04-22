#!/usr/bin/env python3
"""
Automate gdb-multiarch commands with pygdbmi
Equivalent to:
    gdb-multiarch ../apps/gordon/bin/gordon_erase.elf
    target remote localhost:3333
    monitor reset halt
    load
    continue
"""

from pygdbmi.gdbcontroller import GdbController
import sys
import time
import shutil

# ELF_FILE = "../apps/gordon/bin/gordon_erase.elf"
# GDB_CMD = ["gdb-multiarch", "--interpreter=mi3", ELF_FILE]


def run_gdb_commands(elf_file, gdb_port=3333, no_gdb_reset = False):
    
    tool = check_gdb_multiarch_version()

    print(f"[INFO] Launching GDB with ELF: {elf_file}")
    gdb_cmd = [tool, "--interpreter=mi3", elf_file]

    gdbmi = GdbController(command=gdb_cmd)

    def send_cmd(cmd, wait=1.0):
        """Send command to gdb and print structured response"""
        # print(f"\n[CMD] {cmd}")
        responses = gdbmi.write(cmd, timeout_sec=10)  # increase timeout
        time.sleep(wait)
        # for r in responses:
        #     if r["message"]:
        #         print(f"   {r['type']}: {r['message']}")
        return responses

    try:
        # 1. Connect to target via OpenOCD GDB server
        send_cmd(f"target remote localhost:{gdb_port}")

        # 2. Reset and halt
        if no_gdb_reset:
            send_cmd("monitor halt")
        else:
            send_cmd("monitor reset halt")
        send_cmd("set *0x40005060 = 0x0")
        
        # 3. Load ELF file into target
        send_cmd("load", wait=3)

        # 4. Continue execution
        send_cmd("continue", wait=1)

    finally:
        print("\n[INFO] Exiting GDB...")
        gdbmi.exit()

def check_gdb_multiarch_version():
    exe_name = "gdb-multiarch.exe" if sys.platform == "win32" else "gdb-multiarch"
    gdb_path = shutil.which(exe_name)
    err_msg = ""
    if gdb_path:
        print(f"[OK] Found {exe_name} at: {gdb_path}")
        return exe_name
    else:
        err_msg = f"[ERROR] {exe_name} not found in PATH.\n"
        if sys.platform == "win32":
            err_msg = err_msg + "Install or Download from https://static.grumpycoder.net/pixel/gdb-multiarch-windows/gdb-multiarch-16.3.zip. Add gdb-multiarch.exe path to Environment path and try again"
        else:
            err_msg = err_msg + "Install using below commands and try again.\n\tsudo apt update\n\tsudo apt install gdb-multiarch -y"
        
        print(err_msg)
        raise Exception(err_msg)

if __name__ == "__main__":
    try:
        elf_file = "../apps/gordon/bin/gordon_erase.elf"
        gdb_port = 3333
        run_gdb_commands(elf_file, gdb_port)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        sys.exit(0)

