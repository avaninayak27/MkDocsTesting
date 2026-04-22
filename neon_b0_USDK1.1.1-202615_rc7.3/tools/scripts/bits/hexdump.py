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

def hexdump_ascii(data: bytes, length: int = 16, prefix: str = '') -> str:
    FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])
    lines = []
    for i, c in enumerate(range(0, len(data), length)):
        chars = data[c : c + length]
        hex = ' '.join(["%02x" % x for x in chars])
        printable = ''.join(["%s" % ((x <= 127 and FILTER[x]) or '.') for x in chars])
        lines.append(
            "%s%s %04x  %-*s  %s"
            % ('\n' if i > 0 else '', prefix, c, length * 3, hex, printable)
        )
    return ''.join(lines)


def hexdump(data, linesize):
    """
    Return hexdump representation of data.
    data is a bytes object. The returned result is a string.
    """
    prettylines = []
    if len(data) < 65536:
        fmt = "%%04X   %%-%ds"
    else:
        fmt = "%%08X   %%-%ds"
    fmt = fmt % (3 * linesize - 1,)
    for i in range(0, len(data), linesize):
        line = data[i : i + linesize]
        hextext = " ".join('%02x' % b for b in line)
        prettylines.append(fmt % (i, str(hextext)))
    return prettylines


def test_hexdump_ascii():
    expected = [
        'PrEfIx 0000  41 42 43 44 45 46 47 48 49 4a 4b 4c 4d 4e 4f 50   ABCDEFGHIJKLMNOP',
        'PrEfIx 0010  51 52 53 54 55 56 57 58 59 5a 5b 5c 5d 5e 5f 60   QRSTUVWXYZ[.]^_`',
        'PrEfIx 0020  61 62 63 64 65 66 67 68 69 6a 6b 6c 6d 6e 6f 70   abcdefghijklmnop',
        'PrEfIx 0030  71 72 73 74 75 76 77 78 79                        qrstuvwxy',
    ]
    data = bytes(range(ord('A'), ord('z')))
    result = hexdump_ascii(data, prefix='PrEfIx').split("\n")
    if result != expected:
        print("\n".join(result))
        print("\n".join(expected))
        assert False


def test_hexdump():
    expected = ['0000   41 42 43 44            ']
    data = 'ABCD'
    result = hexdump(data.encode(), 8)
    if result != expected:
        print(result)
        print(expected)
        assert False


def main():
    """
    >>> main()
    SUCCESS
    """
    test_hexdump_ascii()
    test_hexdump()
    print('SUCCESS')


if __name__ == '__main__':
    main()
