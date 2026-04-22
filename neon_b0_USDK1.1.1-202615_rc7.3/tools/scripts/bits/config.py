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
Default config module

Shared configuration for this library.
This is not argparse dependent.

"""


from dataclasses import dataclass


@dataclass
class LoggerConfig:
    verbose: int = 0
    debug: int = 0
    log_asctime: bool = False
    log_threadName: bool = False
    log_filename: bool = False
    log_funcName: bool = False

'''
Default HIO GPIO configuration.
Change the values to fit the target platform
'''
@dataclass
class GpioConfig:
    wakeup_pin: int = 2 # for example 14 on SDIO PI hat
    wakeup_level: int = 0 # for example 1 (high) on SDIO
    irq_pin: int = 0
    irq_mode: int = 0
    host_wakeup_pin: int = 0
    host_irq_pin: int = 0


@dataclass
class RpiGpioConfig(GpioConfig):
    wakeup_pin: int = 3
    wakeup_level: int = 0
    irq_pin: int = 4
    irq_mode: int = 2
    host_wakeup_pin: int = 20
    host_irq_pin: int = 21


def dataclass_changes(ref, x):
    s = ''
    for k,v in x.__dict__.items():
        v_ref = getattr(ref, k)
        if v != v_ref:
            s += f'{type(ref).__name__}.{k:<20s}: {v_ref} -> {v}\n'
    return s


def update_from_argparse(dc, opt):
    for k,v in dc.__dict__.items():
        if hasattr(opt, k):
            v = getattr(opt, k)
            setattr(dc, k, v)
