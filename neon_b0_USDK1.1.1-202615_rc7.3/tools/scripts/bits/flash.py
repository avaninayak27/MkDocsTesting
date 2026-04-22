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

import uuid
import enum
import hio.api.flash
from collections import namedtuple
import hashlib

try:
    # is this really how imports like this is supposed to work?
    from bits.hwaddress import HWAddress
    from bits.target_errno import TargetErrno
except ModuleNotFoundError:
    from hwaddress import HWAddress
    from target_errno import TargetErrno
    pass

class FlashError(Exception):
    pass


class PartitionType(enum.IntEnum):
    SYSFS   = 14
    DATA    = 15
    PANIC   = 27
    VIRT    = 29
    BOOT    = 30
    UNUSED  = 31

    # the TYPE entries are here to make it possible to do
    # PartitionType(27) for all valid values of 27
    TYPE_0  = 0
    TYPE_1  = 1
    TYPE_2  = 2
    TYPE_3  = 3
    TYPE_4  = 4
    TYPE_5  = 5
    TYPE_6  = 6
    TYPE_7  = 7
    TYPE_8  = 8
    TYPE_9  = 9
    TYPE_10 = 10
    TYPE_11 = 11
    TYPE_12 = 12
    TYPE_13 = 13
    TYPE_14 = 14
    TYPE_15 = 15
    TYPE_16 = 16
    TYPE_17 = 17
    TYPE_18 = 18
    TYPE_19 = 19
    TYPE_20 = 20
    TYPE_21 = 21
    TYPE_22 = 22
    TYPE_23 = 23
    TYPE_24 = 24
    TYPE_25 = 25
    TYPE_26 = 26
    TYPE_27 = 27
    TYPE_28 = 28
    TYPE_29 = 29
    TYPE_30 = 30
    TYPE_31 = 31
    pass


def name_to_enum(base: enum.IntEnum, name):
    """
    >>> name_to_enum(PartitionType, 'virt').name
    'VIRT'
    """
    for k,v in base.__members__.items():
        if k.lower() == name.lower():
            return base(v)
    return None


class SecureBootMode(enum.Enum):
    NONE = enum.auto()
    PUF = enum.auto()
    FUSE = enum.auto()
    pass

class FuseLocation(enum.Enum):
    FLASH = enum.auto()
    FUSE = enum.auto()
    pass

PartitionInfo = namedtuple('PartitionInfo',
                           ('index', 'ptype', 'sect_start', 'sect_count'))

class Progressor():
    def __init__(self):
        self._callback = None
        self._op = None
        self._total = None
        self._current = None
        pass

    def register(self, callback):
        self._callback = callback
        if self._op and callable(self._callback):
            self.callback(self._op, self._total, self._current)
        return

    def start(self, op, total):
        self._op = op
        self._total = total
        self._current = 0
        if callable(self._callback):
            self._callback(self._op, self._total, self._current)
        return

    def advance(self, amount):
        self._current += amount
        if callable(self._callback):
            self._callback(self._op, self._total, self._current)
        return

    def complete(self):
        if callable(self._callback):
            self._callback(self._op, self._total, self._total)
        self._op = None
        self._total = None
        self._current = None
        return

class TargetFlash():
    @staticmethod
    def _chunked(data, sliceobj):
        start, stop, step = sliceobj.indices(len(data))
        for o in range(start, stop, step):
            n = min(o+step, stop)
            yield o, data[o:n]
        return

    def __init__(self, dev):
        # print("TargetFlash.__init__")
        rsp = dev.call(hio.api.flash.identify)
        if rsp.status != 0:
            raise FlashError('failed to identify flash', rsp.status)

        self.dev = dev

        self.page_size = rsp.page_size
        self.sector_size = rsp.sector_size
        self.num_pages = rsp.num_pages
        self.idcode = rsp.idcode

        self._progress = Progressor()
        pass

    @property
    def capacity(self):
        return self.page_size * self.num_pages

    @property
    def capacity_sectors(self):
        return int(self.page_size * self.num_pages / self.sector_size)

    def register_progress(self, callback):
        return self._progress.register(callback)

    def pread(self, *, count, offset):
        if offset < 0:
            raise ValueError('offset must be positive')

        if count < 0:
            raise ValueError('count must be positive')

        if offset >= self.capacity:
            return b''

        if count == 0:
            return b''

        count = min(count, self.capacity - offset)

        result = bytearray()

        self._progress.start('read', count)
        while count > 0:
            amount = min(count, self.dev.hiomaxsize - 48)
            rsp = self.dev.call(hio.api.flash.read, offset, amount, timeout = 10)
            if rsp.status != 0:
                break
            result.extend(rsp.data)
            count -= amount
            offset += amount
            self._progress.advance(amount)

        self._progress.complete()
        return bytes(result)

    def phash(self, *, count, offset):
        print("TargetFlasher.phash called")
        rsp = self.dev.call(hio.api.flash.hash, offset, count)
        if rsp.status != 0:
            raise FlashError('flash hash failed', rsp.status)
        return rsp.data

    def check_hash_match(self, data, offset):
        return (self.dev.call(hio.api.flash.hash, offset, len(data)).data == hashlib.sha256(data).digest())

    def pwrite(self, *, data, offset, use_hash=True):
        if offset < 0:
            raise ValueError('offset must be positive')

        if offset >= self.capacity:
            return 0

        amount = 0
        self._progress.start('write', len(data))

        for off, dat in self._chunked(data, slice(0, len(data), 64*1024)):
            off += offset

            if use_hash and self.check_hash_match(dat, off):
                self._progress.advance(len(dat))
                amount += len(dat)
            else:
                limit=self.capacity-off

                for o, d in self._chunked(dat, slice(0, limit,
                                                  self.dev.hiomaxsize - 48)):
                    rsp = self.dev.call(hio.api.flash.write, off+o, len(d), d, timeout = 10)
                    if rsp.status != 0:
                        raise FlashError('flash write failed', rsp.status)
                    amount += len(d)
                    self._progress.advance(len(d))

        self._progress.complete()
        return amount

    def enroll(self, *, secureboot_mode, fuse_location,
               secret, ecdsa_key, fw_key):
        if secureboot_mode not in (SecureBootMode.PUF, SecureBootMode.FUSE):
            raise ValueError('secureboot_mode must be one of SecureBootMode.PUF, SecureBootMode.FUSE')

        if fuse_location not in (FuseLocation.FLASH, FuseLocation.FUSE):
            raise ValueError('fuse_location must be one of FuseLocation.FLASH, FuseLocation.FUSE')

        if len(ecdsa_key) != 64:
            raise ValueError('ecdsa_key must be 64 bytes long')

        if len(fw_key) != 32:
            raise ValueError('fw_key must be 32 bytes long')

        mode = 0
        secret = bytearray(secret)

        if secureboot_mode == SecureBootMode.PUF:
            if len(secret) < 33:
                raise ValueError('SecureBootMode.PUF needs 264 bits of random data as secret')
            del secret[33:]
            mode = 1
        else:
            if len(secret) < 16:
                raise ValueError('SecureBootMode.FUSE needs an AES key as secret')
            del secret[16:]
            mode = 2
            pass

        secret.extend(0 for _ in range(33-len(secret)))

        if fuse_location == FuseLocation.FUSE:
            mode |= 4
            mode |= 8
            pass

        # TODO: quick workaround for the fact that Message.pack
        # expects a list or tuple, not bytes; this should really be
        # fixed there
        secret = list(secret)
        ecdsa_key = list(ecdsa_key)
        fw_key = list(fw_key)

        rsp = self.dev.call(hio.api.flash.enroll, mode, secret, ecdsa_key, fw_key)
        if rsp.status != 0:
            raise FlashError('enroll failed', rsp.status)
        return

    def hash(self, *, offset, count):
        raise NotImplementedError('hash not yet implemented')

    def boot(self, *, address, data):
        raise NotImplementedError('boot not yet implemented')
        return

    def flush(self):
        rsp = self.dev.call(hio.api.flash.flush)
        if rsp.status != 0:
            raise FlashError('flush failed', rsp.status)
        return

    def close(self):
        self.dev.close()
        self.dev = None

    def get_hwaddr(self):
        rsp = self.dev.call(hio.api.flash.get_hwaddr)
        if rsp.status != 0:
            raise FlashError('get_hwaddr failed', rsp.status)
        return HWAddress(rsp.data)

    def set_hwaddr(self, hwaddr):
        rsp = self.dev.call(hio.api.flash.set_hwaddr, hwaddr)
        if rsp.status != 0:
            raise FlashError('set_hwaddr failed', rsp.status)
        return

    def get_uuid(self):
        rsp = self.dev.call(hio.api.flash.get_uuid)
        if rsp.status != 0:
            raise FlashError('get_uuid failed', rsp.status)
        return uuid.UUID(bytes=rsp.data)

    def set_uuid(self, u):
        if isinstance(u, uuid.UUID):
            u = u.bytes
        else:
            u = bytes(u)
            pass
        rsp = self.dev.call(hio.api.flash.set_uuid, u)
        if rsp.status != 0:
            raise FlashError('set_uuid failed', rsp.status)
        return

    def load_partition_table(self):
        rsp = self.dev.call(hio.api.flash.load_partition_table, 0)
        if rsp.status != 0:
            raise FlashError('load_partition_table failed', rsp.status)
        return

    def save_partition_table(self):
        rsp = self.dev.call(hio.api.flash.save_partition_table)
        if rsp.status != 0:
            raise FlashError('save_partition_table failed', rsp.status)
        return

    def _get_partition(self, index):
        rsp = self.dev.call(hio.api.flash.get_partition, index)
        if rsp.status != 0:
            return rsp.status
        return PartitionInfo(index, rsp.type, rsp.sect_start, rsp.sect_count)
        # if rsp.status == TargetErrno.EINVAL:
        #     return None
        # if rsp.status == TargetErrno.ENOENT:
        #     return None
        # if rsp.status != 0:
        #     raise FlashError('get_partition failed', rsp.status)

    def partitions(self):
        self.load_partition_table()
        for index in range(16):
            p = self._get_partition(index)
            if isinstance(p, tuple):
                yield p
                continue
            if p == TargetErrno.EINVAL:
                break
            if p != TargetErrno.ENOENT:
                raise FlashError('unexpected error from get_partition', p)
            pass
        return

    def add_partition(self, *, index, type, sect_start, sect_count):
        rsp = self.dev.call(hio.api.flash.add_partition, index, type,
                            sect_start, sect_count)
        if rsp.status != 0:
            raise FlashError('add_partition failed', rsp.status)
        return

    def delete_partition(self, *, index):
        rsp = self.dev.call(hio.api.flash.delete_partition, index)
        if rsp.status != 0:
            raise FlashError('delete_partition failed', rsp.status)
        return

    def get_partition_object(self, *, pinfo=None, ptype=None):
        if (pinfo is None and ptype is None) or \
           (pinfo is not None and ptype is not None):
            raise ValueErro('exactly one of pinfo and ptype must be specified')

        if ptype is not None:
            for pi in self.partitions():
                if pi.ptype == ptype:
                    pinfo = pi
            if pinfo is None:
                return None

        start = self.sector_size * pinfo.sect_start
        end = start + self.sector_size * pinfo.sect_count

        return Partition(self, start, end)


class Partition():
    def __init__(self, flash, start_addr, end_addr):
        self.flash = flash
        self.start_addr = start_addr
        self.end_addr = end_addr

    @property
    def capacity(self):
        return self.end_addr - self.start_addr

    def pread(self, *, count, offset):
        if offset < 0:
            raise ValueError('offset is negative', offset)
        if offset >= self.end_addr:
            return b''
        size = min(count, self.end_addr - offset)
        return self.flash.pread(count=size, offset=self.start_addr + offset)

    def pwrite(self, *, data, offset):
        if offset < 0:
            raise ValueError('offset is negative', offset)
        if offset >= self.end_addr:
            return 0
        size = min(len(data), self.end_addr - offset)
        return self.flash.pwrite(data=data[:size], offset=self.start_addr + offset)


class FileLike():
    def __init__(self, obj):
        self.obj = obj
        self.offset = 0

    def read(self, size):
        data = self.obj.pread(size, self.offset)
        self.offset += len(data)
        return data

    def write(self, data):
        n = self.obj.pwrite(data, self.offset)
        self.offset += n
        return n

    def tell(self):
        return self.offset

    def seek(self, offset, whence=0):
        if whence == 0:
            pos = offset
        elif whence == 1:
            pos = self.offset + offset
        elif whence == 2:
            pos = self.capacity + offset
        else:
            raise ValueError('invalid whence ({whence!r}, should be 0, 1 or 2)')

        if pos < 0:
            raise ValueError('negative seek position {pos}')
        if pos > self.capacity:
            raise ValueError('seek past end of device {pos}')
        self.offset = pos
        return self.offset

# poor man's progress bar
def progress(title, total, current):
    w = 72 - len(title)

    m = w * current // total
    if m > 0:
        bar = '=' * (m-1) + '>' + ' '*(w-m)
    else:
        bar = ' ' * w
    print(f'\r{title}: [{bar}]', end='')
    return

__all__ = [
    'FlashError',
    'FuseLocation',
    'Partition',
    'PartitionInfo',
    'PartitionType',
    'progress',
    'SecureBootMode',
    'TargetFlash'
    ]
