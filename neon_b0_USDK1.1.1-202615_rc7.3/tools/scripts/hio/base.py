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
##########################################################################.

import json
import struct
import collections
import re
import ipaddress
import inspect
from socket import htonl, ntohl
from bits.hwaddress import HWAddress
from uuid import UUID

import os

def get_enabled_modules():
    # Get the directory where base.py is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'hio_config.json')

    try:
        with open(json_path) as f:
            config = json.load(f)
        return [name for name, data in config.items() if data.get('enable', False)]
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not read configuration file ({e}), using default modules")
        return ['sys', 'debug']

class registry(type):
    """Registry meta-class all modules(groups) and messages"""

    _messages    = collections.defaultdict(list)
    _modules     = {}
    _sys_modules = get_enabled_modules()

    def __init__(cls, name, bases, attrs):
        type.__init__(cls, name, bases, attrs)

        if len(bases) == 0:
            return

        # Add all enumeration items to the message class dictionary
        #
        for obj in list(cls.__dict__.values()):
            if isinstance(obj, dict):
                for key,value in obj.items():
                    setattr(cls, key, value)

        m = inspect.getmodule(cls)
        group_name = getattr(m, 'GROUP_NAME', None)
        group_id = getattr(m, 'GROUP_ID', None)

        if group_name is None or group_id is None:
            raise ValueError('must specify GROUP_NAME and GROUP_ID')

        if not (group_name.isascii() and group_name.isidentifier()):
            raise ValueError(f'GROUP_NAME must be valid identifier, not {group_name!r}')

        if not (0 <= group_id <= 255):
            raise ValueError('GROUP_ID must be in range 0..255')

        if 0 <= group_id <= 127 and group_name not in registry._sys_modules:
            raise ValueError('GROUP_ID should be in rage 128..255 for non-system module')

        cls.group = group_id
        cls.msgid = len(registry._messages[group_name])
        registry._modules[group_name] = group_id
        registry._messages[group_name].append(cls)

    @staticmethod
    def groups():
        """Return a list of all message groups"""
        return tuple(registry._modules.keys())

    @staticmethod
    def group(gid):
        """Return message group by group id"""
        for mod, i in registry._modules.items():
            if i == gid: return mod
        return None

    @staticmethod
    def group_id(group):
        """Return message group id given group name"""
        return registry._modules.get(group, None)

    @staticmethod
    def messages(group):
        """Return a list of all message in specified group"""
        return registry._messages[group]

    @staticmethod
    def dump():
        for mod, i in sorted(registry._modules.items(), key=lambda x:x[1]):
            print("Group {} {}".format(i, mod))
            for j,m in enumerate(registry._messages[mod]):
                print("   {:2d}: {}".format(j, m))


class message(metaclass = registry):
    """Base class for all host API messages"""

    @classmethod
    def get_declaration(cls, name, qual=None):
        result = []
        for field in cls.get_fields(name):
            if field.name.startswith('reserved'):
                continue
            elif qual:
                d = "{} {}".format(qual, field.get_decl())
            else:
                d = field.get_decl()
            result.append(d)
        return result

    @classmethod
    def get_fields(cls, direction):
        return getattr(cls, direction, None)


class field:
    """Base class for all message fields"""

    _regexp = ('(-?(?:0x)?[0-9a-fA-F]+)',)

    def __init__(self, name, default=0, array=None, fmt="{}", doc=''):
        self.name = name
        self.default = default
        self.array = array
        self.prfmt = fmt
        self.doc = doc

    @property
    def ctype(self):
        return type(self)._ctype

    @property
    def pyfmt(self):
        fmt = type(self)._pyfmt
        # Variable size (u)int8_t pack and unpack as byte strings
        if self.array == 0 and fmt.upper() == 'B':
            fmt = 's'
        return fmt

    @property
    def regexp(self):
        if self.array is None:
            r = type(self)._regexp
        else:
            r = string._regexp
        return r

    # convert raw decoded value to something nicer
    def decode_value(self, value):
        return value

    def convert(self, match):
        s = match.group(1)
        if self.array is None:
            val = int(s, 0)
        elif self.array == 0:
            expr = eval(s)
            if isinstance(expr, str):
                val = expr.encode('ascii')
            elif isinstance(expr,tuple) or isinstance(expr, list):
                val = bytes(expr)
            else:
                val = expr
        else:
            val = list([int(x,0) for x in s.split(',')])
        return val

    def from_string(self, actual):
        value = None
        for regexp in self.regexp:
            match = re.match(regexp, actual)
            if match:
                #print("from_string: match={}".format(match))
                value = self.convert(match)
                break
        return value

    def get_decl(self):
        if self.array is None:
            return "{} {}".format(self.ctype, self.name)
        else:
            return "{} {}[{}]".format(self.ctype, self.name, self.array)

    def get_enum(self):
        return []

    def get_assign(self, dst, value):
        if self.array is None:
            return "{} = {};".format(dst, value)
        elif self.array == 0:
            return "/* {} must be set by the caller */".format(self.name)
        else:
            return "memcpy({0}, {1}, sizeof {0});".format(dst, value)

    def __str__(self):
        return "{}({})".format(type(self).__name__, self.name)


class uint8(field):
    _ctype = "uint8_t"
    _pyfmt = "B"


class int8(field):
    _ctype = "int8_t"
    _pyfmt = "b"


class uint16(field):
    _ctype = "uint16_t"
    _pyfmt = "H"


class int16(field):
    _ctype = "int16_t"
    _pyfmt = "h"


class uint32(field):
    _ctype = "uint32_t"
    _pyfmt = "I"


class int32(field):
    _ctype = "int32_t"
    _pyfmt = "i"


class uint64(field):
    _ctype = "uint64_t"
    _pyfmt = "Q"


class int64(field):
    _ctype = "int64_t"
    _pyfmt = "q"


class double(field):
    _ctype = "double"
    _pyfmt = "f"

class string(field):
    _ctype = "char"
    _pyfmt = "s"
    _regexp = ('("[^"]*")', '(\S+)')

    @property
    def regexp(self):
        return string._regexp

    def convert(self, match):
        s = match.group(1)
        if s.startswith('"') and s.endswith('"'):
            s = s[1:-1]
            pass
        return bytes(s, 'ascii')

    def get_assign(self, dst, name):
        return "strncpy({0}, {1}, {2});".format(dst, name, self.array)


class pathname(string):
    _regexp = ('("[a-zA-Z0-9./]*")',)

    def __init__(self, name, **kw):
        super().__init__(name, array=68, **kw)

    @property
    def regexp(self):
        return pathname._regexp


class status(int32):
    def __init__(self):
        super().__init__("status", doc='result status, zero is success')


class macaddr(uint8):
    _pyfmt = "s"
    _regexp = ('((?:[0-9a-fA-F]{2,2}:){5,5}(?:[0-9a-fA-F]{2,2}))',)

    def __init__(self, name, **kw):
        super().__init__(name, array=6, **kw)

    @property
    def regexp(self):
        return r'(\S+)',

    def decode_value(self, value):
        return HWAddress(value)

    def convert(self, match):
        return HWAddress.from_string(match.group(1))

class ipaddr4(uint32):
    _regexp = (r'(\d+\.\d+\.\d+\.\d+)', r'(\d+)')

    def decode_value(self, value):
        return ipaddress.ip_address(ntohl(value))

    def convert(self, match):
        try:
            a = int(match.group(1))
        except ValueError:
            pass
        return htonl(int(ipaddress.ip_address(match.group())))

class ipaddr6(uint8):
    _pyfmt   = "s"
    _regexp = ('((^([0-9a-fA-F]{4}|0)(\:([0-9a-fA-F]{4}|0)){7}$))',)

    def __init__(self, name, numaddr=1, **kw):
        arraylen = numaddr*16
        super().__init__(name, array=arraylen, **kw)

    @property
    def regexp(self):
        return ipaddr6._regexp

    def convert(self, match):
        return bytes(ipaddress.ip_address(match.group()).packed)

class uuid(uint8):
    _pyfmt = "s"

    def __init__(self, name, **kw):
        super().__init__(name, array=16, **kw)

    @property
    def regexp(self):
        return r'(\S+)'

    def convert(self, match):
        u = UUID(match.group(1))
        return u.bytes()
