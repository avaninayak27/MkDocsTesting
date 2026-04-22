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
HIO proxy over jtag.

Example:

$ # terminal 1
$ openocd -s sdk-files/ -f ftdi.cfg -f t2.cfg

$ # terminal 2
$ ./script/arden.py apps/gordon-jtag.elf

$ # terminal 3
$ ./script/arden_flash.sh apps/stw.elf krn.trace=R:0x3ff
"""


import os
import sys
import time
import socket
import logging
import argparse
from pprint import pprint
from enum import IntEnum
from collections import namedtuple

# extra
from elftools.elf.elffile import ELFFile
from openocd import OpenOcd
from bits.argparsing import default_parser
from bits.logsetup import config_logger
# from bits import bootrom


logger = logging.getLogger(__name__)


MAGIC = 0xfefd39f


def get_parser():
    """
    >>> get_parser().parse_args(['apps/app.elf']).elf
    'apps/app.elf'
    """
    parser = default_parser()
    parser.add_argument('--elf', default='../apps/gordon/bin/gordon_swd.elf',
                        help='The gordon-jtag.elf image that is loaded on target, needed to lookup symbols information''')
    parser.add_argument('--host', default='localhost', help='OpenOCD server host')
    parser.add_argument('--port', type=int, default=10000, help='port to listen for hio commands')
    parser.add_argument('--tcl_port', type=int, default=6666, help='tcl port to connect to openocd')

    # last is default
    parser.add_argument('--no-rom-check', dest='rom_check', action='store_false')
    parser.add_argument('--rom-check', dest='rom_check', action='store_true')

    # last is default
    parser.add_argument('--magic-check', dest='magic_check', action='store_true')
    parser.add_argument('--no-magic-check', dest='magic_check', action='store_false')

    return parser


class jtag_work_action_e(IntEnum):
    """
    >>> jtag_work_action_e.WRITE.value
    1
    """
    IDLE = 0
    WRITE = 1
    READ = 2


def hio_len_from_buf(data):
    """
    >>> hio_len_from_buf(bytes([2, 0, 1, 2, 3, 4]))
    2
    >>> hio_len_from_buf(bytes([2, 1, 1, 2, 3, 4]))
    258
    """
    return data[1] << 8 | data[0]


def trim_hio_buf(data):
    """
    >>> trim_hio_buf(bytes([2, 0, 1, 2, 3, 4])).hex()
    '02000102'
    """
    size = hio_len_from_buf(data)
    return data[0:size+2]


Sym = namedtuple('Sym', 'addr,size')


class Syms:
    _basename = 'g_jtag_work_'

    write_buf : Sym = None
    read_buf : Sym = None

    action : Sym = None
    count : Sym = None

    start_ts : Sym = None
    stop_ts : Sym = None
    diff_ts : Sym = None

    magic : Sym = None

    def __init__(self, elf_img):
        with open(elf_img, 'rb') as f:
            elf = ELFFile(f)
            symtab = elf.get_section_by_name('.symtab')
            for sym in symtab.iter_symbols():
                if sym.name.startswith(self._basename):
                    v = Sym(sym.entry.st_value, sym.entry.st_size)
                    setattr(self, sym.name.replace(self._basename, ''), v)
        self.check_load()

    def check_load(self):
        missing = []
        for k,v in self.__dict__.items():
            if k.startswith('_'):
                continue
            if v is None:
                missing.append(self._basename + k)
        if len(missing) > 0:
            raise SystemExit(f'Oops: unable to read addr of sym(s) {missing}')

    def __str__(self):
        delimiter = '\n\t'
        members = []
        for (k,v) in self.__dict__.items():
            if k.startswith('_'):
                continue
            members.append(f'{k}={v}')
        return delimiter.join([f'<{self.__class__.__name__}'] + members + ['>'])


class Gordon:
    syms: Syms = None

    def __init__(self, elf_img):
        self.syms = Syms(elf_img)

    def hio_write(self, ocd, data):
        ts = time.time()
        ocd.writemem(self.syms.write_buf.addr, data)
        ocd.write32(self.syms.action.addr, jtag_work_action_e.WRITE.value)
        self.wait_action(ocd)
        logger.debug(f'jtag write {len(data)} bytes complete in {(time.time() - ts)/1000.0:3.3f} ms')

    def hio_read(self, ocd):
        ts = time.time()
        ocd.write32(self.syms.action.addr, jtag_work_action_e.READ.value)
        self.wait_action(ocd)

        data = ocd.readmem(self.syms.read_buf.addr, min(32, self.syms.read_buf.size))
        size = hio_len_from_buf(data) + 2
        if size > len(data):
            data = ocd.readmem(self.syms.read_buf.addr, size)
        logger.debug(f'jtag readmem {size} bytes complete in {(time.time() - ts)/1000.0:3.3f} ms')
        return trim_hio_buf(bytes(data))

    def wait_action(self, ocd, timeout=2, seconds=0.000_005, expected=0):
        logger.debug(f'wait_action: {expected}')
        stop = time.time() + timeout

        while True:
            if time.time() > stop:
                raise TimeoutError(f'action != {expected}, gordon elf may need to be reloaded')
            #v = ocd.read32(self.syms.diff_ts.addr)
            #if v > 0:
            #    us = v + 100
            time.sleep(seconds)
            v = ocd.read32(self.syms.action.addr)
            if v == expected:
                return


class Client:
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address


class HioServer:
    def __init__(self, port, host='localhost'):
        self.client = None
        self.reqs = []
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        server_address = (host, port)
        print('starting up on {} port {}'.format(*server_address))
        sock.bind(server_address)
        sock.listen(1)
        self.sock = sock

    def shutdown(self):
        self.close()
        self.sock.close()

    def wait_connection(self):
        self.sock.settimeout(2)
        client = Client(*self.sock.accept())
        logger.warning(f'{client.address} connected')
        self.client = client

    def close(self):
        if self.client is None:
            return
        client = self.client
        logger.warning(f'{client.address} closed the connection')
        client.connection.close()
        self.client = None

    def send(self, req):
        logger.debug(f'tcp send {len(req)} {hexdump(req)}')
        self.client.connection.sendall(req)

    def recv(self):
        data = self.client.connection.recv(64_000)
        logger.debug(f'tcp recv {len(data)} {hexdump(data)}')
        return data


def hexdump(data: bytes):
    """
    >>> hexdump(list(range(0, 4)))
    '00 01 02 03'
    """
    if data is None:
        return ''
    xx = []
    for x in data:
        xx.append(f'{x:02x}')
    return ' '.join(xx)


# class OCDMemory(bootrom.Memory):
#     def __init__(self, ocd : OpenOcd):
#         self.ocd = ocd

#     def read_bytes(self, addr, size) -> bytes:
#         return bytes(self.ocd.readmem(addr, size))


class AppState:
    app : Gordon = None
    ocd : OpenOcd = None
    opt = None

    ocd_connected: bool = False
    req = None
    resp = None

    def ocd_notify(self, connected):
        self.ocd_connected = connected
        if not connected:
            # print('lost connection with openocd')
            pass


def strip_speed_change(req):
    """
    This hack is NOT safe!
    """
    nums = b'0123456789'
    last = 0
    for i in range(1, min(12, len(req))):
        if req[i] in nums:
            last = i+1
        else:
            break
    return req[0:last], req[last:]


def tests():
    v = strip_speed_change(b'@921600')
    assert (b'@921600', b'') == v

    v = strip_speed_change(b'@921600\x02\x0012')
    assert (b'@921600', b'\x02\x0012') == v


tests()


def do_magic_check(state):
    v = None
    try:
        v = state.ocd.read32(state.app.syms.magic.addr)
    except TypeError:
        pass
    if v != MAGIC:
        print(f'magic check failed {MAGIC} != {v}, force terminate connection')
        # raise SystemExit('reasons!')
        raise Exception(f'magic check failed {MAGIC} != {v}, force terminate connection')


def do_rom_check(state, OpenOCD_port):
    print('(re)connecting with openocd')
    state.ocd.connect(state.opt.host, port=OpenOCD_port)
    
    # rom_version = bootrom.read_rom_version(OCDMemory(state.ocd))
    # print(f'boot rom version of connected device: "{rom_version}"')

import threading
class hio_server(threading.Thread):
    def __init__(self, elf_path, OpenOCD_port, hioserver_port = 10000):
        threading.Thread.__init__(self)
        self.elf_path = elf_path
        self.OpenOCD_port = OpenOCD_port
        self.hioserverport = hioserver_port
        self._running = True
        self.startDone = False
        self.terminate_success = False
        self.err_msg = ""
    def terminate(self):
        self._running = False
        while 1:
            if self.terminate_success:
                break
        
    def run(self):
        elf_path = self.elf_path
        OpenOCD_port = self.OpenOCD_port
        server = None
        
        try:
            parser = get_parser()
            opt = parser.parse_args() #sys.argv[1:])
            if elf_path:
                opt.elf = elf_path
            config_logger(opt)
        
            state = AppState()
            state.app = Gordon(opt.elf)
            state.opt = opt
            opt.port = self.hioserverport
            logger.debug(state.app.syms)
        
            state.ocd = OpenOcd(notify=state.ocd_notify)
            if state.ocd.openocd_start_code> 0:
                self.err_msg = "Error connecting to OpenOCD"
                return
        
            if opt.rom_check:
                do_rom_check(state, OpenOCD_port)
        
            if opt.magic_check:
                state.app.wait_action(state.ocd)
                do_magic_check(state)
            
            server = HioServer(opt.port)
            print(f'HioServer started successfully on {opt.host} port {opt.port}')
            self.startDone = True
            err_msg = ""
            while True:
                reset = True
                if not self._running:
                    break
                
                try:
                    if server.client is None:
                        server.wait_connection()
                        req = server.recv()
                        if req == b'':
                            server.close()
                            continue
                        speed, state.req = strip_speed_change(req)
                        if state.req == b'':
                            state.req = None
                    
                    if not state.ocd_connected:
                        do_rom_check(state, OpenOCD_port)
                        state.app.wait_action(state.ocd)

                    if state.resp:
                        server.send(state.resp)
                        state.resp = None

                    if state.req is None:
                        req = server.recv()
                        if req == b'':
                            server.close()
                            continue
                        state.req = req

                    do_magic_check(state)

                    req = state.req
                    state.req = None
                    logger.debug(f'from tcp  size={len(req)} {hexdump(req)}')
                    state.app.hio_write(state.ocd, req)
                    
                    state.resp = state.app.hio_read(state.ocd)
                    logger.debug(f'from jtag size={len(state.resp)} {hexdump(state.resp)}')
        
                    reset = False  # if  we got this far, no reset is needed
                    
                except TimeoutError as e:
                    # print(e)
                    err_msg = str(e)
                    if "gordon elf may need to be reloaded" in str(e):
                        raise Exception(str(e))
                except BrokenPipeError as e:
                    print(type(e))
                    print(e)
                    print(req)
                    err_msg = str(e)
                except ConnectionResetError as e:
                    print(type(e))
                    print(e)
                    print(req)
                    err_msg = str(e)
                except ConnectionRefusedError as e:
                    err_msg = str(e)
                    pass
                except Exception as e:
                    # print("Timeout exception from while", type(e), str(e))
                    err_msg = str(e)

                if "magic check failed" in err_msg:
                    raise Exception(err_msg)
                if "gordon elf may need to be reloaded" in err_msg:
                    raise Exception(err_msg)
                pass
        
                try:
                    if reset:
                        state.req = None
                        state.resp = None
                        server.close()
                        state.ocd.disconnect()
                except Exception:
                    pass
            
            state.ocd.disconnect()
            server.shutdown()
            print("HioServer shutdown sucess")
            
        except Exception as e:
            # print("Exception in arden_swd.main: ", str(e))
            self.err_msg = str(e)
            try:
                state.ocd.disconnect()
            except: pass
            try:
                server.shutdown()
            except: pass
            print("Exception: HioServer shutdown sucess")
            pass
        
        finally:
            self.terminate_success = True
            
            # try:
            #     state.ocd.disconnect()
            # except: pass
            # try: 
            #     server.shutdown()
            # except:
                # pass
            # print("HioServer shutdown sucess")
            pass

if __name__ == '__main__':
    parser = get_parser()
    opt = parser.parse_args()
    elf_file = opt.elf
    OpenOCD_port = opt.tcl_port
    hioserver_port = opt.port

    # hio_serv = hio_server("../apps/gordon/bin/gordon_swd.elf", 6666, 10000)
    hio_serv = hio_server(elf_file, OpenOCD_port, hioserver_port)
    hio_serv.start()


    while not hio_serv.startDone:
        time.sleep(0.01)
        if hio_serv.err_msg:
            break
    
    if hio_serv.err_msg:
        print("error at hio_serv.err_msg", hio_serv.err_msg)
    
    hio_serv.join()
    try:
        if not hio_serv.terminate_success:
            hio_serv.terminate()
    except Exception as e:
        pass

    
    
