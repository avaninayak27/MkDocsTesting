#!/usr/bin/env python3
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

"""
Interface to OpenOCD daemon.

This module implements an interface class to the OpenOCD daemon and provides
functions for controlling the target execution and reading and writing memory.
"""


import sys
import os
import re
import socket
import logging
from argparse import ArgumentParser
from sys import platform

logger = logging.getLogger(__name__)


def parse_openocd_version(version: str):
    """
    Given a version string, return version tuple.

    >>> parse_openocd_version('Open On-Chip Debugger 0.10.0')
    (0, 10, 0, '')

    >>> parse_openocd_version('Open On-Chip Debugger 0.11.0+dev-00418-g918811529 (2021-10-11-10:48)')
    (0, 11, 0, '+dev-00418-g918811529 (2021-10-11-10:48)')

    """
    m = re.search('.* ([0-9]+).([0-9]+).([0-9+])(.*)', version)
    v1 = int(m.group(1))
    v2 = int(m.group(2))
    v3 = int(m.group(3))
    txt = m.group(4)
    return (v1, v2, v3, txt)


class OpenOcdOps:
    def read8(self, addr):
        if platform == "linux" or platform == "linux2":
            return 'ocd_mdb {:#x}'.format(addr)
        else:
            return 'mdb {:#x}'.format(addr)

    def read16(self, addr):
        if platform == "linux" or platform == "linux2":
            return 'ocd_mdh {:#x}'.format(addr)
        else:
            return 'mdh {:#x}'.format(addr)

    def read32(self, addr):
        if platform == "linux" or platform == "linux2":
            return 'ocd_mdw {:#x}'.format(addr)
        else:
            return 'mdw {:#x}'.format(addr)

    def halt(self):
        if platform == "linux" or platform == "linux2":
            return 'capture "ocd_halt"'
        else:
            return 'capture "halt"'

    def input(self):
        if platform == "linux" or platform == "linux2":
            return 'ocd_echo $input'
        else:
            return 'return $input'

class OpenOcdOps11(OpenOcdOps):
    def read8(self, addr):
        return 'mdb {:#x}'.format(addr)

    def read16(self, addr):
        return 'mdh {:#x}'.format(addr)

    def read32(self, addr):
        return 'mdw {:#x}'.format(addr)

    def halt(self):
        return 'capture "halt"'

    def input(self):
        return 'return $input'


class OpenOcd:

    COMMAND_TOKEN = '\x1a'

    def __init__(self, verbose=False, notify=lambda x:None):
        self.verbose = verbose
        self.notify = notify
        self.sock = None
        self.ops : OpenOcdOps = None
        self.openocd_start_code = 0

    def set_version(self, version):
        """
        In version 0.11.0 if OpenOCD, some commmands where renamed.

        This function will configure this class for the specific version.

        Auto detect will be done by self.connect()
        """
        print(f'openocd version: {version!r}')
        (v1, v2, v3, txt) = parse_openocd_version(version)
        if v1 > 0 or v2 >= 11:
            self.ops = OpenOcdOps11()
        elif v1 == 0 and v2 <= 10:
            self.ops = OpenOcdOps()
        else:
            raise SystemExit(f'Unknown ocd version "{version!r}"')

    def version_check(self):
        version = self.send('version')
        self.set_version(version)

    def connect(self, host="localhost", port=6666):
        """Connect to the OpenOCD daemon at specified host and port."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.openocd_start_code = self.sock.connect_ex((host, port))
        if self.openocd_start_code > 0:
            self.sock.settimeout(10)
            self.sock.shutdown(1)
            self.sock.close()
            return
             
        self.chipname = self.send("set x $CHIPNAME")
        self.notify(True)
        self.version_check()

    def disconnect(self):
        """Disconnect from the OpenOCD daemon."""
        self.notify(False)
        if self.sock:
            try:
                self.sock.settimeout(10)
                self.send("exit")
            except Exception as e:
                pass
            try:
                self.sock.settimeout(10)
                self.sock.shutdown(1)
                self.sock.close()
            except Exception as  e:
                pass

    def send(self, cmd):
        """Send a command string to TCL parser. Return the result that was read."""
        assert self.sock, "Not connected"
        data = (cmd + OpenOcd.COMMAND_TOKEN).encode("ascii")
        logger.debug("<- %r", data)
        self.sock.send(data)
        return self.recv()

    def recv(self):
        """Read from the stream until COMMAND_TOKEN is received."""
        assert self.sock, "Not connected"
        data = bytes()
        while True:
            chunk = self.sock.recv(4096)
            if chunk == b'':
                self.notify(False)
                self.sock.close()
                self.sock = None
                return b''
            data += chunk
            if bytes(OpenOcd.COMMAND_TOKEN, encoding="ascii") in chunk:
                break
        logger.debug("-> %r", data)
        data = data.decode("ascii").strip()
        data = data[:-1] # strip trailing \x1a
        return data

    def reset(self):
        """Reset and halt the target."""
        self.send("reset halt")

    def halt(self):
        """Halt the target."""
        return self.send(self.ops.halt())

    def resume(self):
        """Resume execution of the target."""
        self.send('resume')

    def state(self):
        """Return the current execution state of the target; 'running' or 'halted'"""
        return self.send("{}.cpu curstate".format(self.chipname))

    def read8(self, addr):
        """Read a 8-bit value from specified address."""
        raw = self.send(self.ops.read8(addr)).strip().split(': ')
        return None if len(raw) != 2 else int(raw[1], 16)

    def read16(self, addr):
        """Read a 16-bit value from specified address."""
        raw = self.send(self.ops.read16(addr)).strip().split(': ')
        return None if len(raw) != 2 else int(raw[1], 16)

    def read32(self, addr):
        """Read a 32-bit value from specified address."""
        raw = self.send(self.ops.read32(addr)).strip().split(': ')
        return None if len(raw) != 2 else int(raw[1], 16)

    def readx(self, addr, size):
        """Read value from 'addr' using specified access size (in bytes)"""
        read_fn = getattr(self, "read{:d}".format(8*size))
        return read_fn(addr)

    def write8(self, addr, value):
        """Write 8-bit value to the specifed address."""
        self.send("mwb {:#x} {:#x}".format(addr, value))

    def write16(self, addr, value):
        """Write 16-bit value to the specifed address."""
        self.send("mwh {:#x} {:#x}".format(addr, value))

    def write32(self, addr, value):
        """Write 32-bit value to the specifed address."""
        self.send("mww {:#x} {:#x}".format(addr, value))

    def writex(self, addr, value, size):
        """Write 'value' to 'addr' using specified access size (in bytes)"""
        write_fn = getattr(self, "write{:d}".format(8*size))
        return write_fn(addr, value)

    def readmem(self, addr, n, size = 1):
        """Read a range of 'n' consecutive locations of specified 'size',
        starting at 'addr', and return the values as a list."""
        self.send("array unset input")
        self.send("mem2array input {:d} {:#x} {:d}".format(8*size, addr, n))
        output = self.send(self.ops.input()).split(' ')
        # Array is returned on the form <idx> <val> <idx> <val> ... <idx> <val>
        indices = map(int, output[::2])
        values = []
        for x in output[1::2]:
            values.append(int(x, base=0))
        pairs = dict(zip(indices, values))
        return [int(pairs[i]) for i in range(len(output)//2)]

    def writemem(self, addr, values, size = 1):
        """Write a range of consecutive locations of specified 'size',
        starting at 'addr', using a sequence of values."""
        N = 1024 # Size of chunks to write
        if os.name == 'nt': N = 128 # Smaller chunks for Windows
        for chunk in [values[i:i+N] for i in range(0, len(values), N)]:
            array = " ".join([("{:d} {:#x}".format(a, b)) for a, b in enumerate(chunk)])
            self.send("array unset output")
            self.send("array set output {{ {:s} }}".format(array))
            self.send("array2mem output {:d} {:#x} {:d}".format(8*size, addr, len(chunk)))
            addr += len(chunk) * size


def main():
    parser = ArgumentParser()
    parser.add_argument('--halt', action='store_true', help='Halt target')
    parser.add_argument('--reset', action='store_true', help='Reset and run target')
    parser.add_argument('hostname', default='localhost', help='Hostname for OpenOCD server')
    opt = parser.parse_args(sys.argv[1:])

    ocd = OpenOcd()
    ocd.connect(opt.hostname)

    if opt.halt:
        ocd.halt()
    elif opt.reset:
        ocd.reset()
        ocd.resume()
    else:
        print(ocd.state())

    sys.exit(0)


if __name__ == '__main__':
    main()
