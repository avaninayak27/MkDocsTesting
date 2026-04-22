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

import argparse
import array
import difflib
import io
import sys

from elftools.elf.elffile import ELFFile
try:
    # is this really how imports like this is supposed to work?
    import bits.elf_notes as elf_notes
except ModuleNotFoundError:
    import elf_notes
    pass

class BootArguments():
    @classmethod
    def add_arguments(cls, main):
        main.add_argument('--bootarg-address', metavar='ADDRESS',
                          help='Address to load boot arguments at')
        main.add_argument('--bootarg-elf', metavar='FILENAME',
                          # ELF file to obtain boot arguments from
                          help=argparse.SUPPRESS)
        main.add_argument('--bootarg-sanitize', action='store_true',
                          help=argparse.SUPPRESS)
        main.add_argument('bootargs', metavar='key=value', nargs='*', help='Boot arguments')
        return

    @classmethod
    def factory(cls, options=None, **kw):
        kls = cls
        args = []
        kwargs = {}
        if options:
            if options.bootarg_address is not None:
                kwargs['output_address'] = options.bootarg_address
                pass
            if options.bootarg_elf is not None:
                kwargs['elf_file'] = options.bootarg_elf
                kls = BootArgumentsELF
            elif 'image' in options and options.image is not None:
                kwargs['elf_file'] = options.image
                kls = BootArgumentsELF
                pass
            if 'bootargs' in options:
                args = options.bootargs
                pass
            if 'bootarg_sanitize' in options:
                kwargs['sanitize'] = options.bootarg_sanitize
                pass
            pass
        ba = kls(**kwargs)
        for a in args:
            ba.add(a)
            pass
        return ba

    def __init__(self, output_address=0xc0000, **kw):
        self.output_address = output_address
        self.args = []
        self.argc = 0
        self.argv = 0
        self.load_address = 0
        self.blob = b''
        pass

    def add(self, descr):
        self.args.append(descr)
        return

    def print_args(self):
        print('Unable to determine known boot arguments')
        return

    @staticmethod
    def align(n, a):
        return n + (a - n % a) % a

    def encode(self, start_address=None, end_address=None, sizealign=1):
        if not self.args:
            self.argc = 0
            self.argv = 0
            self.load_address = 0
            self.blob = b''
            return

        argv_offset = array.array('I')
        output = io.BytesIO()
        for a in self.args:
            argv_offset.append(output.tell())
            output.write(a.encode('utf-8') + b'\0')
            pass

        self.argc = len(argv_offset)
        strsize = self.align(output.tell(), 4)
        totsize = strsize + (self.argc + 1) * 4
        padsize = self.align(totsize, sizealign) - totsize

        if start_address is not None:
            self.load_address = self.align(start_address, 256)
        elif end_address is not None:
            self.load_address = self.align(end_address - totsize - 255, 256)
        else:
            self.load_address = self.align(self.output_address - totsize - 255, 256)
            pass

        self.argv = self.load_address + strsize
        #pad
        output.write(b'\0'*(strsize - output.tell()))

        for i,a in enumerate(argv_offset):
            argv_offset[i] += self.load_address
            pass

        argv_offset.append(0)
        argv_offset.tofile(output)
        output.write(b'\0' * padsize)

        self.blob = output.getvalue()
        return
    pass

class BootArgumentsELF(BootArguments):
    def __init__(self, elf_file=None, sanitize=False, **kw):
        super().__init__(**kw)
        self.known_args = {}
        self.sanitize = sanitize
        if elf_file is not None:
            self.extract_known_args(elf_file)
            pass
        pass

    def extract_known_args(self, elf_file):
        elf_fp = None
        if isinstance(elf_file, (str, bytes)):
            elf_fp = open(elf_file, 'rb')
            elf_file = ELFFile(elf_fp)
        elif not isinstance(elf_file, ELFFile):
            elf_file = ELFFile(elf_file)
            pass

        for sec in elf_file.iter_sections():
            if sec.header.sh_type != 'SHT_NOTE':
                continue
            for n in elf_notes.ElfNote.iter_notes(sec.data()):
                if not isinstance(n, elf_notes.InnophaseBootArgNote):
                    continue
                if n.bootarg_name in self.known_args:
                    print('{!r} multiply defined'.format(n.bootarg_name), file=sys.stderr)
                    continue
                self.known_args[n.bootarg_name] = n
                pass
            pass

        if elf_fp:
            elf_fp.close()
        return

    def print_args(self):
        real_args = []
        real_args = [ n
                      for k,n in sorted(self.known_args.items())
                      if not n.bootarg_altname ]
        if not real_args:
            print('No known arguments')
            return
        print('Known arguments:')
        for n in real_args:
            print('  ', n.help())
            pass
        return

    def print_matches(self, name):
        possibilities = [ k for k in self.known_args.keys()
                          if not self.known_args[k].bootarg_altname ]
        matches = difflib.get_close_matches(name, possibilities)

        if not matches and not self.sanitize:
            return

        print('Unknown boot argument {!r}'.format(name), file=sys.stderr, end=' ')
        if len(matches) > 1:
            print('perhaps you mean one of:', file=sys.stderr)
        elif matches:
            print('perhaps you mean:', file=sys.stderr)
        else:
            print('', file=sys.stderr)
            pass
        for m in matches:
            m = self.known_args[m]
            print('    {}'.format(m.help()), file=sys.stderr)
            pass
        return

    def lookup_bootarg(self, name):
        if not self.known_args:
            return None
        n = self.known_args.get(name, None)
        if n is None:
            self.print_matches(name)
            return None

        seen = [n]
        while n.bootarg_altname:
            nn = self.known_args.get(n.bootarg_metavar, None)
            if nn is None:
                print('Boot argument {} is replaced by unknown {} (programming error)'.format(n.bootarg_metavar, n.bootarg_name), file=sys.stderr)
                return None
            if nn in seen:
                print('Boot argument {!r} has circular definition (programming error)'.format(seen[0].bootarg_metavar),
                      file=sys.stderr)
                return None
            seen.append(nn)
            n = nn
            pass

        if seen[0].bootarg_altname:
            print('Boot argument {!r} is obsolete, replacing with {!r}'.format(seen[0].bootarg_name,
                                                                               n.bootarg_name), file=sys.stderr)
            pass

        if n.bootarg_superseded:
            print((f'Boot argument {n.bootarg_name!r} '
                   f'is superseded by {n.bootarg_metavar!r}'),
                  file=sys.stderr)
            pass

        return n

    def parse_integer(self, name, value):
        try:
            int(value, 0)
        except ValueError:
            print('Boot argument {!r} is an integer, unknown value {!r}'.format(name, value), file=sys.stderr)
            pass
        return name + '=' + value

    def parse_boolean(self, name, value):
        if value is None:
            return '{}=1'.format(name)
        if value.lower() in ('yes', 'true', 'y', 't'):
            return '{}=1'.format(name)
        if value.lower() in ('no', 'false', 'n', 'f'):
            return '{}=0'.format(name)
        try:
            v = int(value)
            if v == 0:
                return '{}=0'.format(name)
            if v != 1:
                print('Boot argument {!r} is a boolean, not an integer'.format(name), file=sys.stderr)
                pass
            return '{}=1'.format(name)
        except ValueError:
            print('Boot argument {!r} is a boolean, unknown value {!r}'.format(name, value), file=sys.stderr)
            pass
        return name + '=' + value

    def add(self, descr):
        if '=' in descr:
            an, av = descr.split('=', 1)
        else:
            an, av = descr, None
            pass

        n = self.lookup_bootarg(an)
        if n is None:
            return super().add(descr)
        if n.bootarg_typename == 'integer':
            return super().add(self.parse_integer(n.bootarg_name, av))

        if n.bootarg_typename == 'bool':
            return super().add(self.parse_boolean(n.bootarg_name, av))

        if av is None:
            return super().add(n.bootarg.name)
        return super().add(n.bootarg_name + '=' + av)
    pass


def hexdump(address, data):
    while data:
        s = ['{:02x}'.format(c) for c in data[:16]]
        t = [ chr(c) if chr(c).isprintable() else '.' for c in data[:16]]
        print('{:05x}: {:48} : {}'.format(address, ' '.join(s), ''.join(t)))
        address += 16
        data = data[16:]
        pass
    return

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--foo')
    ap.add_argument('image')
    BootArguments.add_arguments(ap)
    opt = ap.parse_args()

    ba = BootArguments.factory(options=opt)

    ba.print_args()
    print()

    ba.encode()
    print('argc={}, argv={:#x}'.format(ba.argc, ba.argv))
    hexdump(ba.load_address, ba.blob)
    pass
