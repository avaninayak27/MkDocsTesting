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

import struct
import io

ELFNOTE_TYPE_PATCH  = 1
ELFNOTE_TYPE_HWVERSION  = 2
ELFNOTE_TYPE_BOOTARG  = 3

class ElfNote():
    match_name = None
    match_type = None
    def __init__(self, type, name, desc):
        self.note_type = type
        self.note_name = name
        self.note_desc = desc
        pass
    @staticmethod
    def zbytes(data, offset=0):
        n = data.find(b'\0', offset)
        return data[offset:n]
    @classmethod
    def factory(cls, type, name, desc):
        work = cls.__subclasses__()
        cbest = None
        while work:
            c = work.pop()
            if c.match_name == name and c.match_type == type:
                return c(type, name, desc)
            work.extend(c.__subclasses__())
            if cbest is None and c.match_name == name:
                cbest = c
                continue
            pass
        if cbest:
            return cbest(type, name, desc)
        return cls(type, name, desc)

    @classmethod
    def iter_notes(cls, note_segment):
        offset = 0
        while offset + 12 <= len(note_segment):
            nl, dl, t = struct.unpack_from('<III', note_segment, offset)
            offset += 12
            nd = note_segment[offset:offset + nl]
            offset += (nl+3)&-4
            dd = note_segment[offset:offset + dl]
            offset += (dl+3)&-4
            yield cls.factory(t, nd, dd)
            pass
        return
    pass

class InnophaseNote(ElfNote):
    match_name = b'innophase\0'
    pass

class InnophasePatchNote(InnophaseNote):
    match_type = ELFNOTE_TYPE_PATCH

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.patchid, self.symbol, self.target = \
            struct.unpack_from('<III', self.note_desc, 0)
        self.target_name = self.zbytes(self.note_desc, 12).decode('ascii')
        pass

    @property
    def name(self):
        # backwards compatibility
        return self.target_name
    pass

class InnophaseHWVersionNote(InnophaseNote):
    match_type = ELFNOTE_TYPE_HWVERSION

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.hardware_version = self.zbytes(self.note_desc, 0).decode('ascii')
        pass
    def __str__(self):
        return 'Hardware version: {}'.format(self.hardware_version)
    pass

class InnophaseBootArgNote(InnophaseNote):
    match_type = ELFNOTE_TYPE_BOOTARG

    typenames = {
        'string': 0,
        'bool': 1,
        'integer': 2,
        'altname': 256,
        'superseded': 257
    }

    def read_pbytes(self, f):
        l = int.from_bytes(f.read(1), 'little')
        return f.read(l).decode('ascii')

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        f = io.BytesIO(self.note_desc)
        self.bootarg_version = int.from_bytes(f.read(4), 'little')
        self.bootarg_type = int.from_bytes(f.read(4), 'little')
        self.bootarg_flags = int.from_bytes(f.read(4), 'little')
        self.bootarg_name = self.read_pbytes(f)
        self.bootarg_metavar = self.read_pbytes(f)
        self.bootarg_descr = self.read_pbytes(f)
        f.close()
        pass

    @property
    def bootarg_typename(self):
        for k, v in self.typenames.items():
            if v == self.bootarg_type:
                return k
        return '?' + str(self.bootarg_type)

    @property
    def bootarg_altname(self):
        return self.bootarg_type == self.typenames['altname']

    @property
    def bootarg_superseded(self):
        return self.bootarg_type == self.typenames['superseded']

    def help(self):
        if self.bootarg_altname:
            return '{}: obsolete, use {}'.format(self.bootarg_name,
                                                 self.bootarg_metavar)
        if self.bootarg_superseded:
            return '{}: superseded by {}'.format(self.bootarg_name,
                                                  self.bootarg_metavar)
        return '{}={} <{}>: {}'.format(self.bootarg_name,
                                       self.bootarg_metavar,
                                       self.bootarg_typename,
                                       self.bootarg_descr)

    def __str__(self):
        return 'Boot argument: {}'.format(self.help())
    pass

if __name__ == '__main__':
    from elftools.elf.elffile import ELFFile
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument('file')
    opt = ap.parse_args()

    e = ELFFile(open(opt.file, 'rb'))

    for sec in e.iter_sections():
        if sec.header.sh_type != 'SHT_NOTE':
            continue
        for n in ElfNote.iter_notes(sec.data()):
            print(n)
            pass
        pass
    pass
