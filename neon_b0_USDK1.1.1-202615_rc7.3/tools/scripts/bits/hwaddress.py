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

import enum
import re

class HWAddress(bytes):
    r"""
    >>> vector = [
    ...     ('00:11:22:33:44:55', '00-11-22-33-44-55', b'\x00\x11"3DU'),
    ...     ('0:1:2:3:4:5', '00-01-02-03-04-05', b'\x00\x01\x02\x03\x04\x05'),
    ...     ('00-11-22-33-44-55', '00-11-22-33-44-55', b'\x00\x11"3DU'),
    ...     ('0-1-2-3-4-5', '00-01-02-03-04-05', b'\x00\x01\x02\x03\x04\x05'),
    ...     ('001122334455', '00-11-22-33-44-55', b'\x00\x11"3DU'),
    ...     ('0011.2233.4455', '00-11-22-33-44-55', b'\x00\x11"3DU')
    ... ]
    >>> for a, b, c in vector:
    ...    m = HWAddress.from_string(a)
    ...    assert m == c
    ...    assert HWAddress(m) == c
    ...    assert str(m) == b
    """

    class Format(enum.Enum):
        CANONICAL = enum.auto()
        LEGACY = enum.auto()
        BIT_REVERSED = enum.auto()
        pass

    def __new__(self, value):
        if len(value) != 6:
            raise ValueError('hardware address must be 6 bytes')
        return bytes.__new__(self, value)

    def to_string(self, *, format=Format.CANONICAL):
        """
        >>> addr = HWAddress.from_string('AC-DE-48-12-7B-80')
        >>> addr.to_string(format=HWAddress.Format.CANONICAL)
        'ac-de-48-12-7b-80'
        >>> addr.to_string(format=HWAddress.Format.LEGACY)
        'ac:de:48:12:7b:80'
        >>> addr.to_string(format=HWAddress.Format.BIT_REVERSED)
        '35:7b:12:48:de:01'
        """
        if format == HWAddress.Format.CANONICAL:
            return '-'.join(f'{c:02x}' for c in self)

        if format == HWAddress.Format.LEGACY:
            return ':'.join(f'{c:02x}' for c in self)

        if format == HWAddress.Format.BIT_REVERSED:
            def bitreverse(b):
                return int(f'{b:08b}'[::-1], 2)
            return ':'.join(f'{bitreverse(c):02x}' for c in self)

        raise ValueError(f'{format!r} not a valid format')

    def __str__(self):
        return self.to_string()

    @classmethod
    def from_string(cls, string):
        '''This function parses a string as a mac-address. It accepts single
        or double hex digits separated with either colon, dash or period,
        and double hex digits without separators, leading and trailing
        white space is ignored.

        Return true on success, or false on malformed strings.

        Example input:
          a-b-c-d-e-f
          aa-bb-cc-dd-ee-ff
          aa:b:c:d:ee:ff
          aabbccddeeff
          aabb.ccdd.eeff

        Degenerate forms are also accepted:
          aabb-cc:dd.eef
        '''
        pattern = r'([0-9a-fA-F]{1,2})[-:.]?' * 5 + r'([0-9a-fA-F]{1,2})' + r'$'

        m = re.match(pattern, string.strip())
        if not m:
            raise ValueError('{!r} is not a valid hardware address'.format(string))
        return cls(bytes(int(x, 16) for x in m.groups()))
    pass

if __name__ == '__main__':
    import doctest
    doctest.testmod()
    pass
