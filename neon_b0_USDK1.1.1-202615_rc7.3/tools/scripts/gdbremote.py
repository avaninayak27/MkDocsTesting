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
Provides a GDB server on port 3333.

A GDB client can connect to this server to
access coredump memory etc.

Ex:

    $ ./script/gdbremote.py --core coredump.bin

Will start a GDB server with a previously retrieved
coredump file (coredump.bin).

To inspect the coredump, start gdb-multiarch for the
ELF that generated the coredump:

    $ gdb-multiarch helloworld.elf
    (gdb) target remote localhost:3333
    (gdb) info registers

and use GDB normally.

Please reference the Talaria TWO documentation for
further information and available debugging commands.

"""
import os
import time
from sys import platform
import sys
import re
import socket
import codecs
import select
import struct
import logging
import errno
from binascii import unhexlify
from elftools.elf.elffile import ELFFile
from bits.bootargs import BootArgumentsELF

class GDB(object):

    SOF = b'$'
    EOF = b'#'
    ACK = b'+'
    NAK = b'-'
    INTERRUPT = b'\x03'

    ESCAPE = ord('}')

    MAX_PACKET = 16384

    SIGNAL_TRAP = 5

    def __init__(self, verbose=False):
        self.con = None
        self.log = logging.getLogger('GDB')
        self.log.setLevel('DEBUG' if verbose else 'INFO')
        logging.basicConfig(stream=sys.stderr)
        codecs.register(lambda x: (GDB.encode,GDB.decode,None,None) if x == "gdb" else None)

    @staticmethod
    def encode(buf):
        """Encode GDB message escaping certain bytes"""
        result = bytearray()
        for x in buf:
            if x in (ord('#'), ord('$'), ord('*'), ord('}')):
                result.append(GDB.ESCAPE)
                x ^= 0x20
            result.append(x)
        return (bytes(result), len(buf))

    @staticmethod
    def decode(buf):
        """Decode GDB message with escaped bytes"""
        result = bytearray()
        inbuf = iter(buf)
        for x in inbuf:
            if x == GDB.ESCAPE:
                result.append(next(inbuf) ^ 0x20)
            else:
                result.append(x)
        return (bytes(result), len(buf))

    @staticmethod
    def chop(buf, n):
        """Chop up a bytes object in chunks of n in reversed order"""
        while len(buf) > 0:
            yield buf[-n:]
            buf = buf[:-n]

    @staticmethod
    def swap(buf):
        """Reverse the byte order of hex encoded bytes"""
        return ''.join(GDB.chop(buf, 2))

    def unpack(self, pkt):
        if pkt[0] != ord(GDB.SOF) or pkt[-3] != ord(GDB.EOF):
            raise Exception('bad packet')
        if (sum(pkt[1:-3]) % 256) != int(pkt[-2:], 16):
            raise Exception('bad checksum')
        return pkt[1:-3]

    def wait(self, timeout=30.0):
        if platform == "linux" or platform == "linux2":
            p = select.epoll()
            p.register(self.con.fileno(), select.POLLIN)
            try:
                while True:
                    ready = p.poll(timeout)
                    if len(ready) == 0:
                        ret = -1
                    else:
                        rsp = self._readpkt().decode('ascii')
                        if rsp[0] == 'T':
                            self.remove_breakpoints()
                            ret = int(rsp[1:], 16)
                            break
            except KeyboardInterrupt:
                self.interrupt()
                raise
            return ret
        elif platform == "darwin":
            print("OSX detected! Platform is currently not supported")
            ret = 0
            return ret
        elif platform == "win32":
            loop_cnt = int((timeout * 2))
            try:
                for x in range(loop_cnt):
                    time.sleep(0.5)
                    rsp = self._readpkt().decode('ascii')
                    if rsp[0] == 'T':
                        self.remove_breakpoints()
                        ret = int(rsp[1:3], 16)
                        break
                return ret
            except KeyboardInterrupt:
                self.interrupt()
                raise
        
    def send(self, cmd, binary=b''):
        assert isinstance(cmd,str)
        assert isinstance(binary,bytes)
        buf = codecs.encode(cmd.encode('ascii') + binary, 'gdb')
        cksum = bytes("{:02x}".format(sum(buf) % 256), 'ascii')
        frame = GDB.SOF + buf + GDB.EOF + cksum
        self.con.send(frame)
        ack = self.con.recv(1)
        if len(ack) == 0:
            raise Exception("connection closed")
        if ack != GDB.ACK:
            raise Exception("send error")
        if False: self.log.debug('> {}'.format(frame))

    def readpkt(self):
        while True:
            pkt = self._readpkt()
            if not pkt:
                break;
            if pkt != b'OK' and pkt[0] == ord('O'):
                if self.verbose:
                    string = codecs.decode(pkt[1:], 'hex')
                    sys.stdout.write(string.decode('ascii'))
            else:
                break
        return pkt

    def _readpkt(self):
        pkt = bytes()
        self.con.settimeout(60)
        while True:
            try:
                c = self.con.recv(1)
            except BlockingIOError:
                self.con.settimeout(1)
                break
            self.con.settimeout(1)
            if not c:
                break
            pkt += c
            if c == GDB.INTERRUPT and len(pkt) == 1:
                return pkt
            elif c == GDB.EOF:
                if not GDB.SOF in pkt:
                    raise Exception("bad packet (no start-of-frame)")
                # Trim possible garbage before start-of-frame
                pkt = pkt[pkt.find(GDB.SOF):]
                # Receive two bytes checksum
                pkt += self.con.recv(2)
                try:
                    pkt = self.unpack(pkt)
                except Exception as e:
                    self.log.debug("Unpack error: {}".format(str(e)))
                    self.con.send(GDB.NAK)
                    pkt = bytes()
                    continue
                break
        self.con.send(GDB.ACK)
        if False: self.log.debug("< {}".format(pkt))
        return pkt

class GDBclient(GDB):

    def __init__(self, verbose=False):
        super().__init__()
        self.con = None
        self.verbose = verbose
        self.elf = None
        self.name_as_bytes = False
        self.breakpoints = set()

    def connect(self, host, port=3333):
        self.con = socket.create_connection((host, port), timeout=1)
        if False: self.io.start()

    def disconnect(self):
        if self.con:
            self.con.close()

    def cmd(self, cmd, binary=b''):
        self.send(cmd, binary)
        rsp = self.readpkt()
        return rsp.decode('ascii')

    def check_ok(self, rsp, cmd):
        if rsp != "OK":
            raise Exception("{}: {}".format(cmd, rsp))

    def detach(self):
        rsp = self.cmd('D')
        self.log.debug("detach: {}".format(rsp))
        self.check_ok(rsp, "detach")

    def interrupt(self):
        self.con.send(GDB.INTERRUPT)
        rsp = self.readpkt().decode('ascii')
        assert rsp[0] == 'T'
        self.remove_breakpoints()
        return int(rsp[1:], 16)

    def status(self):
        rsp = self.cmd('?')
        assert rsp[0] == 'S'
        return int(rsp[1:],16)

    def get_reg(self, regno):
        rsp = self.cmd("p{:x}".format(regno))
        return int(GDB.swap(rsp), 16)

    def set_reg(self, regno, value):
        rsp = self.cmd("P{:x}={}".format(regno, GDB.swap("{:08x}".format(value))))
        self.check_ok(rsp, "set_reg")

    def read_mem(self, addr, length):
        rsp = self.cmd("m{:x},{:x}".format(addr,length))
        return codecs.decode(rsp, 'hex')

    def write_mem(self, addr, data):
        rsp = self.cmd("X{:x},{:x}:".format(addr,len(data)), data)
        self.check_ok(rsp, "write_mem")

    def readx(self, addr, size):
        fmt = {1:'<B', 2:'<H', 4:'<I'}
        result, = struct.unpack(fmt[size], self.read_mem(addr, size))
        return result

    def read8(self, addr):
        return self.readx(addr, 1)

    def read16(self, addr):
        return self.readx(addr, 2)

    def read32(self, addr):
        return self.readx(addr, 4)

    def writex(self, addr, value, size):
        fmt = {1:'<B', 2:'<H', 4:'<I'}
        self.write_mem(addr, struct.pack(fmt[size], value))

    def write8(self, addr, value):
        self.writex(addr, value, 1)

    def write16(self, addr, value):
        self.writex(addr, value, 2)

    def write32(self, addr, value):
        self.writex(addr, value, 4)

    def write_word(self, addr, value):
        self.write32(addr, value)

    def set_bp(self, addr):
        if isinstance(addr, str):
            sym = self.lookup_name(addr)
            if not sym:
                return False
            addr = sym['st_value'] & -2
        self.breakpoints.add(addr)

    def clr_bp(self, addr):
        if isinstance(addr, str):
            sym = self.lookup_name(addr)
            if not sym:
                return False
            addr = sym['st_value'] & -2
        self.breakpoints.remove(addr)

    def insert_breakpoints(self):
        for addr in self.breakpoints:
            rsp = self.cmd("Z0,{:x},2".format(addr))
            self.check_ok(rsp, "insert_breakpoints")

    def remove_breakpoints(self):
        for addr in self.breakpoints:
            rsp = self.cmd("z0,{:x},2".format(addr))
            self.check_ok(rsp, "remove_breakpoints")

    def monitor_cmd(self, cmd):
        rsp = self.cmd("qRcmd,", codecs.encode(cmd.encode('ascii'), 'hex'))
        #self.check_ok(rsp, "monitor_cmd")

    def cont(self):
        self.insert_breakpoints()
        self.send("c")
        
    #def send_cmd(self, cmd):
    #    self.insert_breakpoints()
    #    self.send(cmd)

    def get_section_by_name(self, name):
        if self.name_as_bytes:
            name = bytes(name, 'ascii')
        return self.elf.get_section_by_name(name)

    def addr2name(self, addr):
        sym = self.lookup_addr(addr)
        return sym.name.decode('ascii') if sym else "<{:#x}>".format(addr)

    def lookup_addr(self, addr):
        section = self.get_section_by_name('.symtab')
        for sym in section.iter_symbols():
            start = sym['st_value'] & -2
            end   = start + sym['st_size']
            if start <= addr and addr < end:
                return sym
        return None

    def lookup_name(self, name):
        if self.name_as_bytes:
            name = bytes(name, 'ascii')
        section = self.get_section_by_name('.symtab')
        for sym in section.iter_symbols():
            if sym.name == name:
                return sym
        return None

    def bootargs(self, args, where='__bss_end__'):
        '''Write program arguments at specified location'''
        sym = self.lookup_name(where)
        if not sym:
            return 0,0
        # args is BootArguments object
        args.encode(start_address=sym['st_value'])
        self.write_mem(args.load_address, args.blob)
        return args.argc, args.argv

    def load(self, filename, verbose=False):
        fp = open(filename, "rb")
        self.elf = ELFFile(fp)
        try:
            self.name_as_bytes = isinstance(self.elf.get_section(0).name, bytes)
        except:
            pass
        for ph in self.elf.iter_segments():
            if ph.header.p_type == 'PT_LOAD':
                if verbose: self.log.debug("Loading {p_paddr:#x} {p_memsz:#x}".format(**ph.header))
                addr = ph.header.p_paddr
                data = ph.data()
                while data:
                    n = min(len(data), 4096)
                    self.write_mem(addr, data[:n])
                    data = data[n:]
                    addr += n
        return self.elf.header.e_entry


class GDBserverBase(GDB):

    SOF  = b'$'
    EOF  = b'#'
    ACK  = b'+'
    NAK  = b'-'
    INTR = b'\x03'

    BINARY_CMDS = (ord('X'),)

    def __init__(self, target):
        super().__init__()
        self.target = target
        self.packet_handlers = {
            ord('q') : self.process_q_packet,
            ord('p') : self.process_p_packet,
            ord('P') : self.process_P_packet,
            ord('g') : self.process_g_packet,
            ord('G') : self.process_G_packet,
            ord('m') : self.process_m_packet,
            ord('M') : self.process_M_packet,
            ord('X') : self.process_X_packet,
            ord('Z') : self.process_Z_packet,
            ord('z') : self.process_z_packet,
            ord('s') : self.process_s_packet,
            ord('c') : self.process_c_packet,
            ord('h') : self.process_h_packet,
            ord('?') : self.process_signal_packet,
            ord('H') : self.process_ignored_packet,
            ord('v') : self.process_ignored_packet,
            ord('\x03') : self.process_intr_packet,
        }

    def process_packet(self, pkt):
        self.log.debug('PKT {}'.format(pkt))
        if not pkt:
            self.log.info("CLOSED")
            return True
        cmd, subcmd = pkt[0], pkt[1:]
        if cmd == ord('k'):
            self.log.info("KILLED")
            return True
        handler = self.packet_handlers.get(cmd, None)
        if not handler:
            self.log.debug(cmd, subcmd)
            self.log.info('%r command not handled' % pkt)
            rsp = ''
        else:
            args = subcmd if cmd in self.BINARY_CMDS else re.split(b'[:,=]', subcmd)
            rsp = handler(args)
        self.send(rsp)
        return False

    def process_ignored_packet(self, subcmd):
        return ''

    def process_h_packet(self, subcmd):
        return 'OK'

    def process_p_packet(self, subcmd):
        '''Read single register'''
        regnum = int(subcmd[0], 16)
        value = self.target.read_register(regnum)
        self.log.info('R{:02d} = {:08x}'.format(regnum, value))
        return GDB.swap('{:08x}'.format(value))

    def process_P_packet(self, subcmd):
        '''Write single register'''
        regnum = int(subcmd[0],16)
        value = int(GDB.swap(subcmd[1].decode()),16)
        self.log.info('R{:02d} <- {:08x}'.format(regnum, value))
        return 'OK' if self.target.write_register(regnum, value) else 'E01'

    def process_g_packet(self, subcmd):
        '''Read all registers'''
        values = [self.target.read_register(i) for i in range(16)]
        return ''.join([GDB.swap('{:08x}'.format(x)) for x in values])

    def process_G_packet(self, subcmd):
        '''Write all registers'''
        regvals = map(''.join, zip(*[iter(subcmd[0])]*8))
        for regnum, value in enumerate(regvals):
            try:
                value = int.from_bytes(bytearray.fromhex(value), 'little')
            except ValueError:
                continue
            self.log.info('R{:02d} <- {:08x}'.format(regnum, value))
            self.target.write_register(regnum, value)
        return 'OK'

    def process_m_packet(self, subcmd):
        '''Read memory'''
        addr = int(subcmd[0], 16)
        size = int(subcmd[1], 16)
        self.log.info('READMEM {:d} @ {:#x}'.format(size, addr))
        return ''.join(['{:02x}'.format(x) for x in self.target.read_memory(addr, size)])

    def process_M_packet(self, subcmd):
        '''Write memory'''
        addr = int(subcmd[0], 16)
        size = int(subcmd[1],16)
        data = bytes(subcmd[2])
        self.log.info('WRITEMEM {:d} bytes @ {:#x}'.format(size, addr))
        self.target.write_memory(addr, data)
        return 'OK'

    def process_X_packet(self, subcmd):
        pos = subcmd.find(b':')
        addr, size = map(lambda x:int(x,16), subcmd[0:pos].split(b','))
        self.log.debug("{:#x}:{:d}".format(addr,size))
        if size > 0:
            data = codecs.decode(subcmd[pos:], 'gdb')
            self.log.info('WRITEMEM {:d}/{:d} @ {:#x}'.format(size, len(data), addr))
            self.target.write_memory(addr, data)
        return 'OK'

    def process_Z_packet(self, subcmd):
        addr = int(subcmd[1], 16)
        self.target.add_breakpoint(addr)
        return 'OK'

    def process_z_packet(self, subcmd):
        addr = int(subcmd[1], 16)
        self.target.del_breakpoint(addr)
        return 'OK'

    def process_s_packet(self, subcmd):
        '''Single step'''
        self.target.step()
        return 'T05'

    def process_c_packet(self, subcmd):
        '''Continue'''
        self.target.run()
        return 'OK'

    def process_intr_packet(self, subcmd):
        '''Interrupt'''
        self.target.halt()
        return 'T05'

    def process_signal_packet(self, subcmd):
        return 'S{:02x}'.format(GDB.SIGNAL_TRAP)

    def process_q_packet(self, subcmd):
        if subcmd[0] == b'Supported':
            return 'PacketSize={:x};qXfer:features:read+'.format(GDB.MAX_PACKET)

        elif subcmd[0] == b'Attached':
            return '0'

        elif b'Xfer:features:read:target.xml' in b':'.join(subcmd):
            #self.log.info('Sending target XML')
            return 'l' + self.target.XML

        elif subcmd[0] == b'Rcmd':
            c = unhexlify(subcmd[1]).decode().split()
            cmd, arg = c[0], c[1:]
            self.log.info('MONITOR {}({})'.format(cmd, arg))
            if hasattr(self.target, cmd):
                fn = getattr(self.target, cmd)
                fn(arg)
                return 'OK'
            else:
                self.log.error("Target command '{}' not supported".format(cmd))
                return ''
        else:
            # Not supported, q commands
            rsp = ''

        return rsp

    def run_one_session(self):
        p = select.poll()
        p.register(self.con, select.POLLIN)
        while True:
            p.poll()
            pkt = self.readpkt()
            if self.process_packet(pkt):
                break
        self.con = None
        return

    def run(self):
        raise NotImplementedError('please instantiate subclass')

class GDBserverTCP(GDBserverBase):
    def __init__(self, target, port=3333):
        super().__init__(target)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('localhost', port))
        self.sock.listen(1)
        self.log.info(f'Listening on port {self.port:d}')
        pass

    @property
    def port(self):
        return self.sock.getsockname()[1]


    def run(self):
        while True:
            self.log.debug("Waiting for connection...")
            s, addr = self.sock.accept()
            s.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            self.log.info("New connection from {}".format(addr))
            self.con = s
            self.run_one_session()
            s.close()
        return
    pass

class GDBserver(GDBserverTCP):
    # backwards compatibility
    pass

class GDBserverPipe(GDBserverBase):
    def __init__(self, target, fdesc):
        super().__init__(target)
        self.con = socket.fromfd(fdesc.fileno(), socket.AF_UNIX, socket.SOCK_STREAM)
        self.log.setLevel('ERROR')
        pass

    def run(self):
        self.run_one_session()
        return

class GDBbreakpoint(object):

    def __init__(self, addr, size=2):
        self.addr = addr
        self.size = size
        self.save = None

    def __hash__(self):
        return self.addr

    def __eq__(self, other):
        return self.addr == other.addr

    def __ne__(self, other):
        return self.addr != other.addr

    def __str__(self):
        return 'Breakpoint @ {:#x}'.format(self.addr)

class Register():
    xml_keys = ['name', 'regnum', 'bitsize', 'save-restore', 'type', 'group']

    def __init__(self, regnum, name, bitsize=32, group='general', **kw):
        self.__dict__.update(kw)

        self.regnum = regnum
        self.name = name
        self.value = 0
        self.group = group
        self.bitsize = bitsize

        self.mask = 2**self.bitsize-1
        pass

    def read(self):
        return self.value

    def write(self, value):
        self.value = value & self.mask
        return True

    @property
    def xml(self):
        keys = []

        for k in self.xml_keys:
            v = getattr(self, k.replace('-', '_'), None)
            if v is None:
                continue
            keys.append(f'{k}="{v!s}"')
            pass
        return '<reg {}/>'.format(' '.join(keys))
    pass

class GDBtarget(object):

    @classmethod
    def genreg(cls):
        for n in range(13):
            yield Register(n, f'r{n}')
            pass
        yield Register(13, 'sp', type='data_ptr')
        yield Register(14, 'lr', type='code_ptr')
        yield Register(15, 'pc', type='code_ptr')
        yield Register(16, 'xpsr')

        yield Register(17, 'msp', type='data_ptr', group='system')
        yield Register(18, 'psp', type='data_ptr', group='system')
        yield Register(19, 'primask', bitsize=1, type='int8', group='system')
        yield Register(20, 'basepri', bitsize=8, type='int8', group='system')
        yield Register(21, 'faultmask', bitsize=1, type='int8', group='system')
        yield Register(22, 'control', bitsize=2, type='int8', group='system')


    def __init__(self):
        self.breakpoints = set()
        self.cpureg = {r.regnum: r for r in self.genreg()}
        pass

    @property
    def XML(self):

        general = [r for r in self.cpureg.values() if r.group == 'general']
        system = [r for r in self.cpureg.values() if r.group == 'system']

        result = [
            '<?xml version="1.0"?>',
            '<!DOCTYPE target SYSTEM "gdb-target.dtd">',
            '<target version="1.0">',
            '<feature name="org.gnu.gdb.arm.m-profile">',
            *(r.xml for r in general),
            '</feature>',
            '<feature name="org.gnu.gdb.arm.m-system">',
            *(r.xml for r in system),
            '</feature>',
            '</target>'
        ]
        return ''.join(result)

    def reset(self, *args):
        pass

    def halt(self):
        pass

    def run(self):
        pass

    def step(self):
        pass

    def add_breakpoint(self, addr):
        self.breakpoints.add(addr)
        pass

    def del_breakpoint(self, addr):
        self.breakpoints.remove(addr)
        pass

    def insert_breakpoints(self):
        for bp in self.breakpoints:
            bp.save = self.read_memory(bp.addr, bp.size)
            self.write_memory(bp.addr, b'\xbe\xbe')
        pass

    def remove_breakpoints(self):
        for bp in self.breakpoints:
            self.write_memory(bp.addr, bp.save)
        pass

    def read_register(self, regnum):
        if regnum in self.cpureg:
            return self.cpureg[regnum].read()
        return 0

    def write_register(self, regnum, value):
        if regnum in self.cpureg:
            return self.cpureg[regnum].write(value)
        return False

    def read_memory(self, addr, size):
        return bytes(size)

    def write_memory(self, addr, data):
        return True

class GDBcore(GDBtarget):

    NUM_REG = 17
    COREDUMP_MAGIC = 0x45524f63

    class Memory(bytearray):
        def __init__(self, startaddr, endaddr):
            super().__init__(endaddr-startaddr)
            self.startaddr = startaddr
            self.endaddr = endaddr
            pass
        def __contains__(self, addr):
            return self.startaddr <= addr and addr < self.endaddr
        def __getitem__(self, key):
            if isinstance(key, slice):
                key = slice(key.start-self.startaddr,
                            key.stop-self.startaddr,
                            key.step)
            elif isinstance(key, int):
                key -= self.startaddr
            return super().__getitem__(key)
        pass

    def __init__(self, filename, *, romfile=None):
        super().__init__()
        corefile = open(filename, 'rb')
        self.blocksize = 1024
        self.regions = []

        self.load_regions_from_header(corefile)
        if not self.regions:
            self.guess_regions(corefile)

        for m in self.regions:
            corefile.readinto(m)
            corefile.seek(-corefile.tell() & (self.blocksize-1), 1)
            pass
        regnum = 0
        while True:
            d = corefile.read(4)
            if len(d) < 4:
                break
            self.write_register(regnum, int.from_bytes(d, 'little'))
            regnum += 1
            pass
        if romfile:
            self.load_regions_from_elf(romfile, skip_ram=True)

    def guess_regions(self, corefile):
        size = corefile.seek(0, 2)
        corefile.seek(0)
        ramsize = 0x80000 if size > 0x10000 + 0x40000 else 0x40000

        self.regions.append(self.Memory(0xfc0000, 0xfd0000))
        self.regions.append(self.Memory(0x40000, 0x40000 + ramsize))
        return

    def load_regions_from_elf(self, elffile, skip_ram=False):
        elf = ELFFile(elffile)
        for ph in elf.iter_segments():
            if ph.header.p_type != 'PT_LOAD':
                continue
            addr = ph.header.p_vaddr
            if skip_ram and addr >= 0x40000:
                continue
            data = ph.data()
            m = self.Memory(ph.header.p_vaddr, ph.header.p_vaddr+ph.header.p_memsz)
            assert len(data) == ph.header.p_filesz
            m[:len(data)] = data
            self.regions.append(m)
            pass
        return

    def load_regions_from_header(self, corefile):
        hdr = corefile.read(16)
        if len(hdr) < 16:
            corefile.seek(0)
            return
        hdr = struct.unpack('<IIII', hdr)
        if hdr[0] != self.COREDUMP_MAGIC or hdr[1] not in (128, 1024) or hdr[2] != hdr[3]:
            corefile.seek(0)
            return
        self.blocksize = hdr[1]
        while True:
            s, e = struct.unpack('<II', corefile.read(8))
            if s == 0:
                break
            self.regions.append(self.Memory(s, e))
            pass
        self.regions.pop(-1) # registers are handled separately
        corefile.seek(-corefile.tell() & (self.blocksize-1), 1)
        return

    def read_memory(self, addr, size):
        for m in self.regions:
            if addr in m:
                return m[addr:addr+size]

        return bytes(size)


def run(host, filename, **kwargs):
    gdb = GDBclient()
    gdb.connect(host)
    # Inhibit reset of M3 debug block
    gdb.write16(0xfc0104, 8)
    # Return to crystal clock (40MHz)
    gdb.write8(0xfc0106, 0)
    gdb.monitor_cmd("reset halt")
    entry = gdb.load(filename)
    args = BootArgumentsELF(filename)
    for k, v in kwargs.items():
        args.add(f"{k}={v}")
    argc, argv = gdb.bootargs(args)
    gdb.set_reg(0, argc)
    gdb.set_reg(1, argv)
    gdb.set_reg(15, entry)
    gdb.cont()
    gdb.disconnect()
    return

def is_socket(fdesc):
    """Return true if fdesc is a socket.

    >>> is_socket(socket.socketpair()[0].makefile())
    True

    >>> is_socket(socket.socket().makefile())
    True

    >>> is_socket(open('/dev/null'))
    False

    """
    if fdesc.isatty():
        return False

    sock = socket.fromfd(fdesc.fileno(), socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.getsockname()
    except OSError as e:
        if e.errno == errno.ENOTSOCK:
            return False
    return True


def main():
    import argparse

    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument('--host', default='localhost',
                     help='Host for OpenOCD and console terminal server')
    arg.add_argument('--gdb-port', default=3333, type=int,
                     help='GDB remote protocol port')
    arg.add_argument('--core',
                     help='Read coredump and start server')
    arg.add_argument('--rom', type=argparse.FileType('rb'),
                     help='Load text from ROM')
    opt = arg.parse_args(sys.argv[1:])

    if opt.core:
        core = GDBcore(opt.core, romfile=opt.rom)
        # when run from within gdb, stdin will be a unix socket, try
        # to detect this case here
        if not is_socket(sys.stdin):
            srv = GDBserver(core, port=opt.gdb_port)
        else:
            srv = GDBserverPipe(core, sys.stdin)
            pass
        srv.run()


if __name__ == '__main__':
    main()

# vim: sw=4 expandtab
#
