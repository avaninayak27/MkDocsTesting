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

"""Flash programming interface

This message group defines operations to program serial flash.
"""
import os
import json
from pathlib import Path

from hio.base import message, status
from hio.base import macaddr, uuid
from hio.base import uint8, uint16, uint32

# Automatically set GROUP_NAME and GROUP_ID based on file name and hio_config.json
_FILE_NAME = Path(__file__).stem
_CONFIG_PATH = Path(__file__).parent.parent / 'hio_config.json'

with open(_CONFIG_PATH) as f:
    _CONFIG = json.load(f)

GROUP_NAME = _FILE_NAME
GROUP_ID = _CONFIG[_FILE_NAME]['group_id']

class identify(message):
    '''Check presence of supported serial flash device.'''
    req   = [
    ]
    rsp   = [
        status(),
        uint16('page_size', doc='Size of flash page'),
        uint16('sector_size', doc='Size of flash erase sector'),
        uint32('num_pages', doc='Device capacity in units of flash pages'),
        uint32('idcode', doc='Flash device manufacturer and device code'),
    ]

class read(message):
    '''Read from flash.'''
    req   = [
        uint32('address', doc='Sector address to start reading from'),
        uint32('length', doc='Number of bytes to read'),
    ]
    rsp   = [
        status(),
        uint8('data', array=0, doc='Data read from flash'),
    ]

class write(message):
    '''Write to flash.'''
    req   = [
        uint32('address', doc='Sector address where write should start'),
        uint32('length', doc='Number of bytes to write'),
        uint8('data', array=0, doc='Data to write to flash'),
    ]
    rsp   = [
        status(),
    ]

class hash(message):
    '''calculate hash of flash.'''
    req   = [
        uint32('address', doc='Sector address to start reading from'),
        uint32('length', doc='Number of bytes to read'),
    ]
    rsp   = [
        status(),
        uint8('data', array=0, doc='Calculated hash of flash'),
    ]

class flush(message):
    '''Flushes any unsaved state to flash.'''
    req   = [
    ]
    rsp   = [
        status(),
    ]
class erase(message):
    '''Erase the chip by sector number'''
    req   = [
        uint32("sector_no",doc='Sector number between 0 to 1023'),
    ]
    rsp   = [
        status(),
    ]
