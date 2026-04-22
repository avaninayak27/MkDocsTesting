#!/usr/bin/env python3
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

  $ pip install pyftdi

  $ # hw1
  $ ftdi_urls.py

  ftdi://ftdi:4232:IN_XHZQ2Q/1   (INP2035 EVK)
  ftdi://ftdi:4232:IN_XHZQ2Q/2   (INP2035 EVK)
  ftdi://ftdi:4232:IN_XHZQ2Q/3   (INP2035 EVK)
  ftdi://ftdi:4232:IN_XHZQ2Q/4   (INP2035 EVK)

  # in this case ftdi_serial=IN_XHZQ2Q

  $ # hw2
  $ ftdi_urls.py

  ftdi://ftdi:4232:610012/1   (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:610012/2   (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:610012/3   (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:610012/4   (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:11003/1    (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:11003/2    (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:11003/3    (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:11003/4    (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:610003/1   (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:610003/2   (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:610003/3   (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:610003/4   (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:610005/1   (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:610005/2   (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:610005/3   (InnoPhase T2 Evaluation Board)
  ftdi://ftdi:4232:610005/4   (InnoPhase T2 Evaluation Board)

  # board 1 have ftdi_serial=610012
  # board 2 have ftdi_serial=11003
  # board 3 have ftdi_serial=610003
  # board 4 have ftdi_serial=610005

"""

import sys
import time
from urllib.parse import urlparse


def list_ftdi_devices():
    from pyftdi.ftdi import Ftdi
    Ftdi.show_devices()


class ftdiurl:
    """
    >>> ftdiurl()
    ftdi://:0x6011/

    >>> ftdiurl(serial='IN_XHZQ2Q')
    ftdi://:0x6011:IN_XHZQ2Q/

    >>> ftdiurl(serial='610012')
    ftdi://:0x6011:610012/

    >>> ftdiurl(path=4)
    ftdi://:0x6011/4

    >>> ftdiurl(4)
    ftdi://:0x6011/4

    >>> ftdiurl().update(path=3)
    ftdi://:0x6011/3

    >>> ftdiurl().from_url('ftdi://:0x6011:IN_XHZQ2Q/4').update(path=2)
    ftdi://:0x6011:IN_XHZQ2Q/2

    """
    __slots__ = ('target', 'serial', 'path')

    def __init__(self, path=None, serial=None, target='ftdi://:0x6011'):
        self.path = path
        self.serial = serial
        self.target = target

    def from_url(self, url):
        x = urlparse(url)
        self.target = f'{x.scheme}://{x.netloc}'
        self.path = x.path.lstrip('/')
        return self

    def update(self, **kwargs):
        for name in kwargs.keys():
            setattr(self, name, kwargs[name])
        return self

    def __repr__(self):
        path = self.path
        if path is None:
            path = ''
        if self.serial is not None:
            return f'{self.target}:{self.serial}/{path}'
        return f'{self.target}/{path}'

    def __str__(self):
        return repr(self)


# This reset is optionally holding console_txd low during reset to inhibit bootloader from flash
def ftdi_reset(url, inhibit=False):
    from pyftdi.gpio import GpioController

    print(f'reset: {url}')
    d, p, t, a = str(url).split(',')
    p, t, a = int(p), float(t), int(a)
    gpio = GpioController()
    gpio.open_from_url(d, direction=1<<p)

    if inhibit:
        console = GpioController()
        url.update(path=4)
        print(f'reset: {url}')
        console.open_from_url(str(url), 1<<1)
        console.write_port(0)
    gpio.write_port(a << p)
    time.sleep(t)
    gpio.write_port((1-a)<<p)
    time.sleep(t)
    if inhibit:
        console.set_direction(1<<1, 0)
    gpio.close()
    if inhibit:
        console.close()
        time.sleep(1)


# This reset is holding console_txd low via on board pulldown connected to PB5, to inhibit bootloader from flash
def reset_noboot(url):
    from pyftdi.gpio import GpioController

    t = 0.1
    r = 128
    p = 32

    print(f'reset: {url}')
    gpio = GpioController()
    gpio.open_from_url(str(url), direction=r|p)
    for x in [0, r, r|p]:
        gpio.write_port(x)
        time.sleep(t)
    gpio.close()


def reset(method, ftdi_serial=None, dev=None):
    url = ftdiurl(serial=ftdi_serial)

    if method == 'none':
        pass

    elif method == 'dev':
        try:
            dev.reset()
        except NotImplementedError:
            print('Reset is not supported by this device', file=sys.stderr)
            sys.exit(1)

        time.sleep(0.5)

    elif method == 'evk42':
        url.path = '2,7,0.1,0'
        ftdi_reset(url)

    elif method == 'evk42_bl':
        url.path = '2,7,0.1,0'
        ftdi_reset(url, True)

    elif method == 'noboot':
        url.path = '2'
        reset_noboot(url)

    elif method.startswith('ftdi'):
        if not ("," in method):
            method = method + ",7,0.1,0"
        ftdi_reset(method)

    elif method == 'ocd':
        from openocd import OpenOcd
        ocd = OpenOcd()
        ocd.connect()
        ocd.reset()
        ocd.resume()

    elif method == 'manual':
        input("Press reset and press ENTER!")

    else:
        print("reset needs to be one of 'none', 'dev', 'evk42', 'evk42_bl', 'ftdi', 'ocd', or 'manual'")
        list_ftdi_devices()
        print('for use with openocd, please append the following to your ftdi.cfg file:')
        print('')
        print('ftdi_serial <serial>')
        print('')
        sys.exit(-1)

import argparse
def main():
    parser = argparse.ArgumentParser(description="Reset EVK Device")
    
    # Optional positional argument (method)
    parser.add_argument(
        "pos_method",
        nargs="?",
        help="Reset Method: evk42, evk42_bl"
    )

    parser.add_argument(
        "--method", "-m",
        type=str,
        default="evk42",
        help="Reset Method: evk42, evk42_bl"
    )

    parser.add_argument(
        "--serial", "-s",
        type=str,
        default=None,
        help="Serial number of the device"
    )

    args = parser.parse_args()

    method = args.method
    if args.pos_method is not None:
        method = args.pos_method

    reset(method, ftdi_serial=args.serial)
    # # reset("ftdi://0x403:0x6011:30005015/2")
    # if len(sys.argv) > 1:
    #     reset(sys.argv[1])
    # else:
    #     reset('evk42')

class ResetError(Exception):
    pass

def reset_evk(device, console=None, inhibitFlashBoot=True):
    pass

if __name__ == '__main__':
    main()
