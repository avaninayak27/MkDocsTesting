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

"""Debug Interface.

This is an interface for debugging. This interface containts operations for:

<ul>
  <li> Force device to halt and stay awake for coredump retrieval </li>
</ul>
"""
import os
import json
from pathlib import Path

from hio import base
from hio.base import uint32
from hio.base import uint16
from hio.base import uint8


# Automatically set GROUP_NAME and GROUP_ID based on file name and hio_config.json
_FILE_NAME = Path(__file__).stem
_CONFIG_PATH = Path(__file__).parent.parent / 'hio_config.json'

with open(_CONFIG_PATH) as f:
    _CONFIG = json.load(f)

GROUP_NAME = _FILE_NAME
GROUP_ID = _CONFIG[_FILE_NAME]['group_id']


"""
class panic(base.message):
    '''Force device to halt and stay awake for coredump retrieval.'''
    req   = [
    ]
    rsp   = [
        base.status(),
    ]


class heartbeat(base.message):
    '''Enable / disable heartbeat indications'''
    req   = [
        uint32("mode", doc='mode, stop(0), count(1), countdown(2)'),
        uint32("count", doc='counter'),
        uint32("delay", doc='delayed start in us'),
        uint32("interval", doc='us'),
        uint32("variance", doc='interval + time() % variance'),
        uint32("pattern", doc='memcpy(0-255), sweep(>255)'),
        uint32("min_avail_heap", doc=''),
        uint16("size", doc=''),
        uint16("reserved", doc=''),
    ]
    rsp   = [
        base.status(),
    ]
    ind   = [
        uint32("pattern", doc='req.pattern % 256'),
        uint32("seq", doc='req.count'),
        uint32("systime"),
        uint32("os_avail_heap"),
        uint8("payload", array=0, doc='payload based on req.pattern'),
    ]

"""
class heap_info(base.message):
    '''Get heap info.'''
    req   = [
    ]
    rsp   = [
        base.status(),
        uint32('heap', doc='heap available'),
    ]

"""
class suspend_info(base.message):
    '''Get heap info.'''
    req   = [
    ]
    rsp   = [
        base.status(),
        uint32('count', doc='suspend count'),
        uint8("payload", array=0, doc='struct history_entry entries[]'),
    ]
"""
