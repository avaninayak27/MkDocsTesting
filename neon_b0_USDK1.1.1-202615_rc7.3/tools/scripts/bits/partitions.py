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


import bits.flash
from collections import namedtuple


def add_comments(data):
    for x in data['partitions']:
        x['_last'] = max(0, x['sect_start'] + x['sect_count'] - 1)
        try:
            x['_ptype'] = bits.flash.PartitionType(x['ptype']).name
        except:
            pass
    return data


def ptype_to_desc(ptype):
    '''
    >>> ptype_to_desc(15)
    'DATA'
    >>> ptype_to_desc(99)
    ''
    '''
    try:
        return bits.flash.PartitionType(ptype).name
    except:
        pass
    return ''

def json_part_to_tflash(part):
    x = {}
    x['index'] = part['index']
    x['type'] = part['ptype']
    x['sect_start'] = part['sect_start']
    x['sect_count'] = part['sect_count']
    return x

def overlap_check(data):
    X = namedtuple('X','first,last,row')
    xx = [X(
        x['sect_start'],
        max(0, x['sect_start'] + x['sect_count'] - 1),
        x) for x in data['partitions']]
    sorted(xx, key = lambda x: x.first)
    overlap = False
    for i, x in enumerate(xx):
        if i == 0:
            continue
        if x.first <= xx[i-1].last:
            overlap = True
            x.row['_comment'] = "WARNING: overlap"
    return overlap


def partition_sanity_check(x, flash_sectors=None):
    '''
    >>> partition_sanity_check({"index": 0, "ptype": 15, "sect_start": 1, "sect_count": 64})
    True
    >>> partition_sanity_check({"index": 0, "ptype": 15, "sect_start": 1, "sect_count": 1})
    False
    >>> partition_sanity_check({"index": 0, "ptype": 15, "sect_start": 1, "sect_count": 600})
    True
    '''
    if flash_sectors is not None:
        if (x['sect_count'] > (flash_sectors - x['sect_start'])):
            x['_comment'] = f'WARNING: flash is only {flash_sectors} sectors'
            return False
    if bits.flash.PartitionType.DATA == x['ptype']:
        if (x['sect_count'] < 8):
            x['_comment'] = 'WARNING: too small, minimum 8 sectors'
            return False
    return True


def partition_table_sanity_check(data, capacity_sectors):
    ok = True
    add_comments(data)
    for x in data.get('partitions', []):
        if not partition_sanity_check(x, capacity_sectors):
            ok = False
    if overlap_check(data):
        ok = False
    return ok
