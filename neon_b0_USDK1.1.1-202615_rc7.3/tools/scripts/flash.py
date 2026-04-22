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

'''
Script to read and write to flash.
(requires gordon.elf)

example:

    ./flash.py part_list
    ./flash.py from_json partition_table.json
    ./flash.py part_write VIRT app.vm

'''


import sys, os
import time
import random
import hostio
import json
import io
import logging
import zipfile
try:
    import gdbremote
except ImportError:
    gdbremote = None
from argparse import ArgumentParser, FileType
from argparse import ArgumentTypeError
from argparse import RawTextHelpFormatter
import hio.base
import hio.api.sys
from reset import reset
from string import ascii_lowercase
import uuid
from bits.hwaddress import HWAddress
import bits.flash
import bits.partitions
from bits.hexdump import hexdump_ascii
from bits.argparsing import parser_append_logging
from bits.logsetup import config_logger


logger = logging.getLogger(__name__)


#
# Compatibity note: This script uses literal string interpolation
# (f-strings) introduced in Python 3.6.
#


def chunked(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))

# this should go someplace generic


def load_keyfile(fileobj):
    try:
        e = json.load(fileobj)
    except Exception:
        raise ValueError(f'{fileobj.name!r} must be a valid json file')

    ck = 'cipher_key'
    pk = 'p256_public'

    if not isinstance(e, dict) \
       or ck not in e \
       or pk not in e:
        raise ValueError(f'{fileobj.name!r} must be an object containing {ck!r} and {pk!r} keys')

    result = {}
    result[ck] = bytes.fromhex(e[ck])
    result[pk] = bytes.fromhex(e[pk])

    return result


def symbolicint(s):
    suffixes = { 'k':2**10, 'K':2**10, 'm':2**20, 'M':2**20 }
    for suffix, magnitude in suffixes.items():
        if s.endswith(suffix):
            return int(s[:-1]) * magnitude
    return int(s, 0)


class SubCommand():
    _sub_commands = []
    def __init_subclass__(cls, cmdname=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.cmdname = cmdname
        if cmdname:
            SubCommand._sub_commands.append(cls)
    @classmethod
    def add_arguments(cls, parser):
        subparser = parser.add_subparsers(dest='cmd', help='Sub commands')
        for c in cls._sub_commands:
            parser = subparser.add_parser(c.cmdname, help=c.__doc__)
            parser.set_defaults(operation=c.execute)
            c.add_arguments(parser)
            pass
        pass


class FlashRead(SubCommand, cmdname='read'):
    '''Read flash'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('--output', type=FileType('wb'), help='Read output filename')
        parser.add_argument('address', type=symbolicint, help='Sector address')
        parser.add_argument('length', type=symbolicint, help='Length in bytes')
        return

    @classmethod
    def execute(cls, tflash, output, address, length, **kw):
        if sys.stdout.isatty():
            tflash.register_progress(bits.flash.progress)

        readbuf = tflash.pread(offset=address, count=length)

        if sys.stdout.isatty():
            tflash.register_progress(None)
            print('')

        if output:
            output.write(readbuf)
            print(f'{len(readbuf)} bytes written to {output.name!r}')
        else:
            print(hexdump_ascii(readbuf, 16))
        return 0


class FlashHash(SubCommand, cmdname='sha256sum'):
    '''hash flash'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('--output', type=FileType('wb'), help='Read output filename')
        parser.add_argument('address', type=symbolicint, help='Sector address')
        parser.add_argument('length', type=symbolicint, help='Length in bytes')
        return

    @classmethod
    def execute(cls, tflash, output, address, length, **kw):
        readbuf = tflash.phash(offset=address, count=length)

        if output:
            output.write(readbuf)
            print(f'{len(readbuf)} bytes written to {output.name!r}')
        else:
            print(hexdump_ascii(readbuf, 16))
        return 0


class FlashWrite(SubCommand, cmdname='write'):
    '''Write flash'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('address', type=symbolicint, help='Sector address')
        parser.add_argument('fdesc', metavar='filename', type=FileType('rb'), help='File to write')
        return

    @classmethod
    def execute(cls, tflash, address, fdesc, **kw):
        if sys.stdout.isatty():
            tflash.register_progress(bits.flash.progress)
        writebuf = fdesc.read()
        amount = tflash.pwrite(data=writebuf, offset=address)
        tflash.flush()
        if sys.stdout.isatty():
            tflash.register_progress(None)
            print('')
        print(f'{amount} bytes written')
        return 0


class FlashErase(SubCommand, cmdname='erase'):
    '''Erase flash'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('sector_start', type=symbolicint, help='Erase from sector (1 sector=4096 bytes)')
        parser.add_argument('sector_stop', type=symbolicint, help='Erase up to sector')
        return

    @classmethod
    def execute(cls, tflash, sector_start, sector_stop, **kw):
        count = sector_stop - sector_start + 1
        byte_count = count * 4096
        print(f'about to erase sector {sector_start}-{sector_stop}, {count:_} sectors ({byte_count:_} bytes)')
        if sys.stdout.isatty():
            tflash.register_progress(bits.flash.progress)
        writebuf = b'\xff' * byte_count
        # TODO: ask target to erase flash, will be much faster
        amount = tflash.pwrite(data=writebuf, offset=4096*sector_start)
        tflash.flush()
        if sys.stdout.isatty():
            tflash.register_progress(None)
            print('')
        print(f'{amount} bytes written')
        return 0


class FlashVerify(SubCommand, cmdname='verify'):
    '''Verify flash content'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('address', type=symbolicint, help='Sector address')
        parser.add_argument('fdesc', metavar='filename', type=FileType('rb'), help='File to verify against')
        return

    @classmethod
    def execute(cls, tflash, address, fdesc, **kw):
        offset = address
        while True:
            expected = fdesc.read(512)
            if not expected:
                break
            actual = tflash.pread(offset=offset, count=len(expected))
            if actual != expected:
                print(f'verify failed at offset {offset}')
                return 1
            offset += len(actual)
            pass
        print('OK')
        return 0


class Enroll(SubCommand, cmdname='enroll'):
    '''Secureboot enrollment'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('--keyfile', type=FileType('r'),
                            required=True,
                            default=None, help='Key filename')
        parser.add_argument('--secureboot',
                            choices=['puf', 'fuse'],
                            default='puf',
                            help='source for secure boot keys')
        parser.add_argument('--fuse-location',
                            choices=['emulated',
                                     'one-time-programmable-fuses'],
                            default='emulated',
                            help='source for fuse bits')
        return

    @classmethod
    def execute(cls, tflash, keyfile, secureboot, fuse_location, **kw):
        print('Enrolling keys')

        secure_keys = load_keyfile(keyfile)

        if secureboot == 'puf':
            mode = bits.flash.SecureBootMode.PUF
            secret = os.urandom(33)
        elif secureboot == 'fuse':
            mode = bits.flash.SecureBootMode.FUSE
            secret = os.urandom(16)
        else:
            raise ValueError('need to specify either puf or fuse for --secureboot')

        if fuse_location == 'emulated':
            fuse = bits.flash.FuseLocation.FLASH
        elif fuse_location == 'one-time-programmable-fuses':
            fuse = bits.flash.FuseLocation.FUSE
            if not sys.stderr.isatty() or not sys.stdin.isatty():
                raise NotImplementedError('this option need user intervention for now')
            print('Using --fuse-location=one-time-programmable-fuses', file=sys.stderr)
            print('    will permanently alter the device.', file=sys.stderr)
            print('', file=sys.stderr)

            key = ''.join(random.sample(ascii_lowercase, k=5))
            key2 = input(f'To proceed enter {key!r}: ')
            if key != key2:
                print('Mismatch, skipping', file=sys.stderr)
                return

        tflash.enroll(secureboot_mode=mode,
                      fuse_location=fuse,
                      secret=secret,
                      ecdsa_key=secure_keys['p256_public'],
                      fw_key=secure_keys['cipher_key'])
        return


def json_pretty(data):
    return json.dumps(data, indent=4)


def parts_to_json(tflash):
    data = {'partitions': []}
    keys = ('index', 'ptype', 'sect_start', 'sect_count')
    for part in tflash.partitions():
        x = {}
        for key in keys:
            x[key] = getattr(part, key)
        data['partitions'].append(x)
    bits.partitions.partition_table_sanity_check(data, tflash.capacity_sectors)
    x = {}
    for k in ('idcode', 'num_pages', 'page_size', 'sector_size'):
        x[k] = getattr(tflash, k)
    data['_identify'] = x
    return data


def print_table(rows, headers):
    rs = []
    rs.append(headers)
    rs.append(['---']*len(headers))
    for row in rows:
        rs.append([str(x) for x in row])
    rs.append(['---']*len(headers))
    rs.append(headers)
    widths = [max(map(len, col)) for col in zip(*rs)]
    for row in rs:
        print("  ".join((val.rjust(width) for val, width in zip(row, widths))))


class PartList(SubCommand, cmdname='part_list'):
    '''List partitions on flash'''
    @classmethod
    def add_arguments(cls, parser):
        return

    @classmethod
    def execute(cls, tflash, **kw):
        sector_count = int(tflash.num_pages * tflash.page_size / tflash.sector_size)
        print(f'flash: id: {tflash.idcode:_x} pages: {tflash.num_pages} page_size: {tflash.page_size} sector_size: {tflash.sector_size} sectors: {sector_count}\n');

        sect_size = tflash.sector_size
        data = parts_to_json(tflash)
        bits.partitions.partition_table_sanity_check(data, tflash.capacity_sectors)
        rows = []
        for x in data.get('partitions', []):
            rows.append([
                x['index'],
                x['ptype'],
                bits.partitions.ptype_to_desc(x.get('ptype', None)),
                x['sect_start'],
                x['sect_count'],
                x['_last'],
                x['sect_start']*sect_size,
                x['sect_count']*sect_size,
                x.get('_comment', '')
            ])
        headers = ['idx',
                'type',
                'desc',
                'sect_start',
                'sect_count',
                'sect_end',
                'bytes_start',
                'bytes_count',
                ]
        print_table(rows, headers)
        return 0


class PartAdd(SubCommand, cmdname='part_add'):
    '''Add a flash partition'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('index', type=symbolicint, help='index')
        parser.add_argument('ptype', type=symbolicint, help='partition type')
        parser.add_argument('sect_start', type=symbolicint, help='start sector')
        parser.add_argument('sect_count', type=symbolicint, help='sector count')
        return

    @classmethod
    def execute(cls, tflash, index, ptype, sect_start, sect_count, **kw):
        tflash.add_partition(index=index, type=ptype, sect_start=sect_start, sect_count=sect_count)
        tflash.save_partition_table()
        print('wrote partition table to flash')


class PartRemove(SubCommand, cmdname='part_remove'):
    '''Add a flash partition'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('index', type=symbolicint, help='index')
        return

    @classmethod
    def execute(cls, tflash, index, **kw):
        tflash.delete_partition(index=index)
        tflash.save_partition_table()
        print('wrote partition table to flash')


def part_index_or_ptype(index_type):
    if index_type.isdigit():
        return int(index_type)
    x = bits.flash.name_to_enum(bits.flash.PartitionType, index_type)
    if x is None:
        raise ArgumentTypeError(f'no type named "{index_type}" in PartitionType')
    return x


def partition_lookup(tflash, index_type):
    sect_size = tflash.sector_size
    if type(index_type) == int:
        for (i, ptype, sect_start, sect_count) in tflash.partitions():
            if i == index_type:
                return sect_size*sect_start, sect_size*sect_count
        SystemError(f'no partition with index {index_type}')
    part = tflash.get_partition_object(ptype=index_type)
    return part.start_addr, part.capacity


class FlashWriteNamed(SubCommand, cmdname='part_write'):
    '''Write a partition to flash based on index or type'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('index_type', type=part_index_or_ptype, help='partition index or type <0|1|2|virt|boot|...>')
        parser.add_argument('f', metavar='filename', type=FileType('rb'), help='File to write')

    @classmethod
    def execute(cls, tflash, index_type, f, **kw):
        start_addr, capacity = partition_lookup(tflash, index_type)
        if sys.stdout.isatty():
            tflash.register_progress(bits.flash.progress)
        writebuf = f.read()
        if len(writebuf) > capacity:
            SystemError(f'size of partition too small {len(writebuf)} < {capacity}')
        amount = tflash.pwrite(data=writebuf, offset=start_addr)
        tflash.flush()
        if sys.stdout.isatty():
            tflash.register_progress(None)
            print('')
        print(f'{amount} bytes written to addr {start_addr}')
        return 0


class FlashReadNamed(SubCommand, cmdname='part_read'):
    '''Read a partition to flash based on index or type'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('index_type', type=part_index_or_ptype, help='partition index or type <0|1|2|virt|boot|...>')
        parser.add_argument('output', type=FileType('wb'), help='File to write')
        return

    @classmethod
    def execute(cls, tflash, index_type, output, **kw):
        start_addr, capacity = partition_lookup(tflash, index_type)
        if sys.stdout.isatty():
            tflash.register_progress(bits.flash.progress)
        readbuf = tflash.pread(offset=start_addr, count=capacity)
        if sys.stdout.isatty():
            tflash.register_progress(None)
            print('')
        if output:
            output.write(readbuf)
            print(f'{len(readbuf)} bytes written to {output.name!r}')
        else:
            print(hexdump_ascii(readbuf, 16))
        return 0


class PartToJson(SubCommand, cmdname='to_json'):
    '''Generate a json file based on what is on flash'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('jsonfile', type=FileType('w'), help='json file that will be written')
        return

    @classmethod
    def execute(cls, tflash, jsonfile, **kw):
        data = parts_to_json(tflash)
        bits.partitions.partition_table_sanity_check(data, tflash.capacity_sectors)
        txt = json_pretty(data)
        jsonfile.write(txt)


class PartFromJson(SubCommand, cmdname='from_json'):
    '''Generate partition table from a json file'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('jsonfile', type=FileType('r'), help='json file to read from')
        return

    @classmethod
    def execute(cls, tflash, jsonfile, **kw):
        data = json.loads(jsonfile.read())
        if not bits.partitions.partition_table_sanity_check(data, tflash.capacity_sectors):
            print(json_pretty(data))
            return
        for part in tflash.partitions():
            logger.warning('delete %s', part)
            tflash.delete_partition(index=part.index)
        tflash.save_partition_table()
        tflash.flush()
        for x in data['partitions']:
            logger.warning('add %s', x)
            tflash.add_partition(**bits.partitions.json_part_to_tflash(x))
        tflash.save_partition_table()
        tflash.flush()
        print('wrote partition table to flash')


class ExtractPanic(SubCommand, cmdname='extract_panic_data'):
    '''Extract data from panic partition'''
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('filename',
                            help='Output filename.')
        return


    @classmethod
    def execute(cls, tflash, filename, **kw):
        p = tflash.get_partition_object(ptype=bits.flash.PartitionType.PANIC)

        filedata = io.BytesIO()

        zf = zipfile.ZipFile(filedata, 'w', compression=zipfile.ZIP_DEFLATED)

        offset = 0

        while True:
            hdr = p.pread(count=8, offset=offset)
            if len(hdr) < 8:
                break
            tag = hdr[:4]
            if tag == b'\xff\xff\xff\xff':
                break
            size = int.from_bytes(hdr[4:], 'little')
            offset += len(hdr)

            data = p.pread(count=size, offset=offset)
            offset += len(data)

            if tag == b'cons':
                fn = 'console.txt'
            elif tag == b'trce':
                fn = 'trace.bin'
            else:
                fn = tag.decode('ascii', errors='replace')
                pass
            if fn in zf.namelist():
                i = 1
                while f"{i}_{fn}" in zf.namelist():
                    i += 1
                    pass
                fn = f"{i}_{fn}"
                pass

            zf.writestr(fn, data)

            offset += -offset % 4
            pass

        zf.close()

        if zf.namelist():
            print(f'Writing {filedata.tell()} bytes to {filename}')
            open(filename, 'wb').write(filedata.getvalue())
        return


def main():
    parser = ArgumentParser(description=__doc__, formatter_class=RawTextHelpFormatter)
    parser.add_argument('--device', default='/dev/ttyUSB2', help='Hostio device name (default: %(default)s)')
    parser.add_argument('--uuid', action='store_true', help='store a new uuid in the flash')
    parser.add_argument('--mac', help='store parameter as mac in flash')
    parser.add_argument('--speed', type=int, default=921600, help='Set interface speed (default: %(default)s)')
    parser.add_argument('--reset', default='none',
                        help='Perform reset using the specified method (default: %(default)s)')
    parser.add_argument('--sync', default=None, help='String used to syncronize on uart')
    parser_append_logging(parser)

    if gdbremote is not None:
        parser.add_argument('--host', default='localhost', help='Hostname for OpenOCD server (default: %(default)s)')
        parser.add_argument('--load', help='Load flash helper via OpenOCD/JTAG')
    parser.set_defaults(operation=PartList.execute)

    SubCommand.add_arguments(parser)

    opt = parser.parse_args(sys.argv[1:])
    config_logger(opt)

    if opt.reset:
        reset(opt.reset)
        time.sleep(0.10)

    if opt.load:
        gdbremote.run(opt.host, opt.load)
        time.sleep(1)

    dev = hostio.open(opt.device, registry=hio.base.registry, speed=opt.speed, sync=opt.sync)
    if not dev:
        sys.exit(1)

    rsp = dev.call(hio.api.sys.query)
    if rsp is None:
        print('Flash helper is not responding, check your cables')
        sys.exit(1)
    if rsp.maxsize < 512+8:
        print('Message maxsize too small ({rsp.maxsize})')
        sys.exit(1)

    tflash = bits.flash.TargetFlash(dev)

    if opt.mac:
        buf = HWAddress.from_string(opt.mac)
        tflash.set_hwaddr(buf)

    if opt.uuid:
        buf = uuid.uuid4()
        tflash.set_uuid(buf)

    if opt.operation:
        opt.operation(tflash, **vars(opt))

    tflash.flush()
    tflash.close()


if __name__ == '__main__':
    main()
