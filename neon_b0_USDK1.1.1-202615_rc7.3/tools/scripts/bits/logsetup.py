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
import logging
from dataclasses import dataclass
from bits.config import LoggerConfig
from bits.config import dataclass_changes
from bits.config import update_from_argparse


logger = logging.getLogger(__name__)


def verbose_to_log_level(count):
    """
    verbose=1  # CRITICAL
    ...
    verbose=5  # DEBUG
    """
    levels = (50, 40, 30, 20, 10, 0)
    level = levels[min(count, len(levels) - 1)]
    return level


def debug_to_flags(conf: LoggerConfig):
    if conf.debug > 0:
        conf.log_threadName = True
    if conf.debug > 1:
        conf.log_funcName = True
    if conf.debug > 2:
        conf.log_filename = True
    if conf.debug > 3:
        conf.log_asctime = True


def config_logger(opt: argparse.Namespace):
    assert (isinstance(opt, argparse.Namespace))
    conf = LoggerConfig()
    update_from_argparse(conf, opt)
    debug_to_flags(conf)

    fmt = ''
    if conf.log_asctime:
        fmt += '{asctime}:15s '
    else:
        fmt += '{relativeCreated:_.3f} ms '
    if conf.log_threadName:
        fmt += '{threadName:<15s} '
    if conf.log_filename:
        fmt += '{filename:<15s} '
    if conf.log_funcName:
        fmt += '{funcName:<15s} '
    fmt += '{message}'
    level = verbose_to_log_level(conf.verbose)
    logging.basicConfig(level=level, style='{', format=fmt)
    for line in dataclass_changes(LoggerConfig(), conf).split('\n'):
        logger.info(line)
