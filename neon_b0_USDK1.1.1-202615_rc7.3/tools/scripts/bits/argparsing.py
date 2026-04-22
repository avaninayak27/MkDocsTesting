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

"""
Update config from argparse when using CLI.

"""


import sys
import logging
import argparse


logger = logging.getLogger(__name__)


def parser_append_logging(parser):
    # see LoggerConfig
    group = parser.add_argument_group('logging')
    group.add_argument('--verbose', '-v', action='count', default=0, help=
                       'multiple -v increase the verbosity (err,warn,info,debug). The maximum is 6.')
    group.add_argument('--debug', '-d', action='count', default=0, help=
                       'multiple -d increase the debug info (thread, func, file). The maximum is 4.')
    group.add_argument('--log_asctime', action="store_true", help='use asctime time format')
    group.add_argument('--log_threadName', action="store_true", help='log threadName')
    group.add_argument('--log_filename', action="store_true", help='log filename')
    group.add_argument('--log_funcName', action="store_true", help='log funcName')
    group.add_argument('--serial', type=str, default="", help='device serial number')
    group.add_argument('--app_elf', type=str, default="", help='Application image elf file')
    group.add_argument('--app_addr', type=str, default="0x00", help='Application image flash address')
    group.add_argument('--dev_conf', type=str, default="", help='Configuration .json file')
    group.add_argument('--fs_img', type=str, default="", help='Filesystem image .img file to write')
    group.add_argument('--fs_addr', type=str, default=0x5FF000, help='Filesystem image start address to write')
    group.add_argument('--out_img', type=str, default="", help='output image .img file for read')
    group.add_argument('--read_addr', type=str, default=0x5FF000, help='Flash start address to read')
    group.add_argument('--read_size', type=str, default=0x200000, help='Size to read')
    group.add_argument('--clear_flash', action='store_true', help='Flag to perform Clear flash')
    group.add_argument('--output', type=str, default="", help='Application image bin file output path')
    group.add_argument('--tfm_app', type=str, default="", help='TFM application image elf/bin file')
    group.add_argument('--ns_app_image_offset', type=str, default=0x400000, help='Non-secured application image offset address')
    group.add_argument('--no_gdb_reset', action='store_true', help='Flag to skip GDB reset via SWD during Clear Flash and Program Flash actions.')
    group.add_argument('--npu_img', type=str, default="", help='NPU Application image (.bin) file to write')
    group.add_argument('--npu_addr', type=str, default=0x00280000, help='NPU Application image start address to write. Default: 0x00280000') #
    group.add_argument('--boot_arg', type=str, default="", help='Boot argument string (space-separated), e.g., "hio.baudrate=921600 hio.maxsize=1600"') #
    group.add_argument('--bootarg_addr', type=str, default=0x00200000, help='Boot arguments start address to write. Default: 0x00200000') #
    group.add_argument('--reset_device', action='store_true', help='Flag to perform device reset')

def default_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser_append_logging(parser)
    return parser
