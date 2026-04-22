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

import time
import logging


logger = logging.getLogger(__name__)


def speed_to_time(speed, num_bytes):
    """
    Calculate transfer time in seconds based on a given (baud rate) speed.

    >>> round(speed_to_time(921_600 , 84_476), 1)  # size of gordon.elf
    0.7

    >>> round(speed_to_time(19_200 , 84_476), 1)
    35.2

    """
    return 8 * num_bytes / speed


class TransferDelay:
    """
    Can be used to force wait for async write to flush.
    poor-mans-synchronization.
    """
    def set_num_bytes(self, num_bytes):
        self.num_bytes = num_bytes
        self.delay = speed_to_time(self.speed, num_bytes)

    def set_sleep(self, seconds):
        self.delay = seconds

    def __init__(self, speed, num_bytes):
        self.speed = speed
        self.set_num_bytes(num_bytes)

    def __enter__(self):
        logger.debug(f'transfer time {self.delay:_.3f} seconds @ {self.speed:_}')
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        time.sleep(max(0, time.time() - self.start + self.delay))


def test_TransferDelay():
    """
    Unit test

    >>> test_TransferDelay()
    0.7
    """
    v = 0
    with TransferDelay(921_600 , 84_476) as x:
        v = round(x.delay, 1)
        x.set_num_bytes(1_000_000)
        x.set_sleep(0)  # speed up testing
    return v
