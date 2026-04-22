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
hostio module

A module that pack/unpack HIO messges
"""


import os
import sys
import time
import struct
import serial
import atexit
import contextlib
from threading import Event
try: import readline
except: readline = None
import threading
import socket
import re
import hio.api.sys
import logging
from bits.speed import speed_to_time
from bits.hexdump import hexdump_ascii
from bits.config import GpioConfig
from bits.config import RpiGpioConfig
from collections import deque
try:
    from spidev import SpiDev
except ImportError as e:
    pass

try:
    import RPi.GPIO as GPIO
except ImportError as e:
    pass

try:
    from pyftdi.spi import SpiController
except ImportError as e:
    pass

try:
    # Needed to register pyftdi as a pyserial backend
    import pyftdi.serialext
except ImportError as e:
    pass


logger = logging.getLogger(__name__)


if sys.version_info.major != 3 or sys.version_info.minor < 3:
    print('Python version 3.3 or higher required (you have {0.major}.{0.minor}.{0.micro})'.format(sys.version_info))
    sys.exit(1)
    pass


class AtomicInt:
    def __init__(self):
        self._lock = threading.Lock()
        self.count = 0

    def inc(self):
        with self._lock:
            self.count += 1
            return self.count
        pass

    def dec(self):
        with self._lock:
            self.count -= 1
            return self.count
        pass


class Message:
    """
    Create objects of this class to pack and unpack hostio message buffers

    >>> str(Message(hio.api.sys.config, 'req').pack(123, 2, 3, 4, 5))
    'config_req(_group=0 _msgid=1 _trxid=123 wakeup_pin=2 wakeup_level=3 irq_pin=4 irq_mode=5)'

    >>> str(Message(hio.api.sys.config, 'rsp').unpack(bytes([0x00, 0x81, 123, 0x00, 0x00, 0x00, 0x00, 0x00])))
    'config_rsp(_group=0 _msgid=129 _trxid=123 status=0)'

    >>> str(Message(hio.api.sys.ping, 'req').pack(123, b'ABC'))
    "ping_req(_group=0 _msgid=4 _trxid=123 payload=b'ABC')"

    """

    def __init__(self, cls, direction):
        assert direction in ('req', 'rsp', 'ind')
        self._name = '{}_{}'.format(cls.__name__, direction)
        self._fields = cls.get_fields(direction)
        self._group = cls.group
        self._msgid = cls.msgid
        self._trxid = None
        self._payload = None

#    def __getattr__(self, name):
#        # try to be backward compatible
#        return getattr(self, '_' + name)

    def pack(self, trxid, *args):
        self._payload = bytearray(struct.pack('<BBH', self._group, self._msgid, trxid))
        self._trxid = trxid
        for field, arg in zip(self._fields, args):
            setattr(self, field.name, arg)
            if field.array is None:
                chunk = struct.pack('<'+field.pyfmt, arg)
            else:
                num = len(arg) if field.array == 0 else field.array
                # if field.maxlen != 0:
                #     assert  num <= field.maxlen, f"Argument exceeding Max Length: {field.maxlen}"
                fmt = '<{:d}{}'.format(num, field.pyfmt)
                if isinstance(arg, list) or isinstance(arg, tuple):
                    chunk = struct.pack(fmt, *arg)
                else:
                    chunk = struct.pack(fmt, arg)
            self._payload.extend(chunk)
        logger.info(self)
        if logger.level <= logging.DEBUG:
            logger.debug('\n' + hexdump_ascii(self._payload, prefix=self._name))
        return self

    def unpack(self, payload):
        self._group, self._msgid, self._trxid = struct.unpack("<BBH", payload[:4])
        self._payload = payload
        pos = 4
        for field in self._fields:
            if field.array is None:
                # not an array
                num = 1
            elif field.array > 0:
                # fixed size array
                num = field.array
            else:
                # variable sized array - the number of elements is deducted
                # from the number of remaining bytes to unpack
                num = len(payload[pos:]) // struct.calcsize(field.pyfmt)
            fmt = '<{:d}{}'.format(num, field.pyfmt)
            chunk = struct.calcsize(fmt)
            value = struct.unpack(fmt, payload[pos:pos+chunk])
            if field.array is None or fmt.endswith('s'):
                assert len(value) == 1, "Expected single value"
                value = value[0]
            value = field.decode_value(value)
            setattr(self, field.name, value)
            pos += chunk
        if False and pos != len(payload):
            print("WARNING: Unpacked {} bytes (received {})".format(pos, len(payload)))
        logger.info(self)
        if logger.level <= logging.DEBUG:
            logger.debug(f'RAW[{len(self._payload)}]\n' + hexdump_ascii(self._payload, prefix=self._name))
        return self

    def is_req(self):
        return self._msgid >> 6 == 0

    def is_rsp(self):
        return self._msgid >> 6 == 2

    def is_ind(self):
        return (self._msgid >> 6) == 3

    def __bool__(self):
        return True

    def __len__(self):
        return len(self._payload)

    def __str__(self):
        values = [f'{x}={getattr(self, x, None):d}' for x in ('_group','_msgid','_trxid')]
        values += [("{}=" + f.prfmt).format(f.name, getattr(self, f.name, None)) for f in self._fields]
        return "{}({})".format(self._name, ' '.join(values))


class HIO(threading.Thread):
    call_mutex = threading.Lock()

    class Error(Exception):
        pass

    class Disconnect(Exception):
        pass

    class HioMaxSizeError(Exception):
        pass

    def __init__(self, path, **kwargs):
        threading.Thread.__init__(self)
        self.name = 'HIO'
        self.setDaemon(True)
        self.path = path
        self.raw = kwargs.get('raw', False)
        self.speed = kwargs.get('speed', 921600)
        self.registry = kwargs.get('registry', None)
        self.com = None
        self.trxid = 0
        self.ind_handler = dict()
        self.rsp_queue = deque()
        self.rsp_sem = threading.Semaphore(0)
        self.wakeup_event = Event()
        self.set_ind_handler(hio.api.sys.wakeup, self.wakeup_callback)
        self.suspend_enabled = False
        self.irq_enabled = False
        self.pending = AtomicInt()
        self.hiomaxsize = 128

    def run(self):
        try:
            while not self.raw:
                reply = self.readmsg()
                if reply is None:
                    continue
                msg = self.unpack(reply)
                if msg is None:
                    pass
                elif msg.is_ind():
                    key = (msg._group, msg._msgid)
                    self.ind_handler.get(key, logging.info)(msg)
                elif msg.is_rsp():
                    if self.pending.dec() == 0:
                        self.target_sleep()
                    self.rsp_queue.append(msg)
                    self.rsp_sem.release()
                else:
                    print("Invalid message: {}".format(msg))
        except HIO.Disconnect:
            print("{}: Disconnected".format(self.path))
        except OSError as e:
            print("{}: {}".format(self.path, e.strerror))
            print(e)
        except Exception as e:
            print('Exception in read loop')
            print(e)
        logging.info('exit read loop')
        return

    def wakeup_callback(self, msg):
        self.wakeup_event.set()

    def enable_suspend(self, enable=True):
        self.suspend_enabled = enable

    def target_sleep(self):
        pass

    def target_wakeup(self):
        pass

    def set_ind_handler(self, cls, fn):
        # Need to add the _ind bits at MSB of msgid
        key = (cls.group, 0xc0 | cls.msgid)
        if fn is None:
            self.ind_handler.pop(key)
        else:
            self.ind_handler[key] = fn

    def next_seq(self):
        result = self.trxid
        self.trxid += 1
        self.trxid &= (2**16-1)
        return result

    def lookup_class(self, buf):
        dirmap = {0:'req', 1:None, 2:'rsp', 3:'ind'}
        group, msgid = struct.unpack('<BB', buf[:2])
        direction = dirmap[msgid >> 6]
        msgid &= 0x3f
        if self.registry:
            mod = self.registry.group(group)
            for cls in self.registry.messages(mod):
                if cls.msgid == msgid:
                    return cls, direction
        return None, None

    def fileno(self):
        return self.com

    def close(self):
        self.raw = True
        self.join()
        if self.com is not None: self.com.close()

    def flushrx(self):
        pass

    def read(self, n):
        raise NotImplementedError()

    def write(self, buf):
        raise NotImplementedError()

    def reset(self):
        raise NotImplementedError()

    def set_timeout(self, timeout):
        # sets timeout to timeout (in seconds), or None for no
        # timeout, return old value
        raise NotImplementedError()

    def get_timeout(self):
        return None

    @contextlib.contextmanager
    def timeout_context(self, timeout):
        # context manager for easier temporary timeout handling
        old = self.set_timeout(timeout)
        try:
            yield self
        finally:
            self.set_timeout(old)
            pass
        return

    def writemsg(self, msg):
        if len(msg) > self.hiomaxsize:
            raise HIO.HioMaxSizeError('Message too large ({} > hio-maxsize({})'.format(len(msg), self.hiomaxsize))
        self.write(struct.pack("<H", len(msg)) + msg._payload)
        return

    def call_async(self, cls, *args):
        assert cls != hio.api.sys.sleep
        self.target_wakeup()
        self.pending.inc()
        trxid = self.next_seq()
        req = Message(cls, 'req').pack(trxid, *args)
        self.writemsg(req)
        return trxid

    def call(self, cls, *args, **kwargs):
        HIO.call_mutex.acquire()
        self.call_async(cls, *args)
        if cls.get_fields('rsp') is None:
            HIO.call_mutex.release()
            return None
        rsp = self.wait_rsp(cls, **kwargs)
        HIO.call_mutex.release()
        return rsp

    def unpack(self, buf):
        cls, direction = self.lookup_class(buf)
        msg = Message(cls, direction)
        msg.unpack(buf)
        return msg

    def wait_rsp(self, cls, timeout=None):
        if not self.rsp_sem.acquire(blocking=True, timeout=timeout):
            return None
        return self.rsp_queue.popleft()

    def readmsg(self):
        hdr = bytes()
        while len(hdr) < 2:
            b = self.read(2 - len(hdr))
            if len(b) == 0:
                return None
            hdr += b
            pass
        msglen, = struct.unpack("<H", hdr)
        msg = bytes()
        while len(msg) < msglen:
            chunk = self.read(msglen - len(msg))
            if len(chunk) == 0:
                print(f'Invalid PKT: Expected {msglen} bytes, got {len(msg)}. '
                      f'timeout was {self.get_timeout()}.'
                      ' Was the timeout to small?')
                logger.critical('\n' + hexdump_ascii(msg, prefix='ERR'))
                return None
            msg += chunk
            pass
        return msg

class Socket(HIO):
    def __init__(self, addr, family=socket.AF_INET, **kwargs):
        super().__init__(addr, **kwargs)
        self.name = 'HIO:Socket'
        self.com = socket.socket(family, socket.SOCK_STREAM)
        if self.raw:
            timeout = None
        else:
            timeout = 0.5
        logger.debug(f'default timeout set to {timeout}')
        self.com.settimeout(timeout)
        if family == socket.AF_INET:
            host, port = addr.split(':')
            self.com.connect((host, int(port)))
            # Send a message with baudrate
            cmsg = bytes('@{}'.format(self.speed), 'ascii')
            self.com.send(cmsg)
        else:
            self.com.connect(addr)
        self.start()
        return

    def read(self, n):
        try:
            buf = self.com.recv(n)
            if len(buf) == 0:
                raise HIO.Disconnect()
        except socket.timeout:
            buf = b''
        return buf

    def write(self, buf):
        return self.com.send(buf)

    def get_timeout(self):
        return self.com.gettimeout()

    def set_timeout(self, timeout):
        old = self.gettimeout()
        logger.debug(f'set_timeout {old} -> {timeout}')
        self.com.settimeout(timeout)
        return old

    def __str__(self):
        return self.path


class Serial(HIO):
    def __init__(self, path, **kwargs):
        super().__init__(path, **kwargs)
        self.name = 'HIO:Serial'
        if self.raw:
            timeout = None
        else:
            timeout = round(0.5 + speed_to_time(self.speed, 2_000), 1)
        logger.debug(f'default timeout set to {timeout} @ {self.speed}')
        self.com = serial.serial_for_url(path, baudrate=self.speed, timeout=timeout)
        self.sync(kwargs.get('sync', None))
        self.start()

    def set_timeout(self, timeout):
        old = self.com.timeout
        logger.debug(f'set_timeout {old} -> {timeout} @ {self.speed}')
        self.com.timeout = timeout
        return old

    def get_timeout(self):
        return self.com.timeout

    def sync(self,cmp):
        if cmp:
            if isinstance(cmp, str):
                cmp = cmp.encode()
            s = b''
            while s != cmp:
                r = self.com.read()
                s += r
                if not cmp.startswith(s):
                    s = r

    def enable_suspend(self, enable=True):
        if enable:
            rsp = self.call(hio.api.sys.config, GpioConfig.wakeup_pin, GpioConfig.wakeup_level, GpioConfig.irq_pin, GpioConfig.irq_mode)
            super().enable_suspend(True)
            self.target_sleep()
        else:
            self.target_wakeup()
            super().enable_suspend(False)
            rsp = self.call(hio.api.sys.config, 0, 0, 0, 0)
        return rsp.status == 0

    def target_sleep(self):
        if self.suspend_enabled:
            # Can't use call_async since that will do wakeup
            self.writemsg(Message(hio.api.sys.sleep, 'req').pack(0))
        return

    def target_wakeup(self):
        if self.suspend_enabled:
            logging.debug('target_wakeup')
            # Previously got spurious wakeup ind, target is awake
            if self.wakeup_event.is_set():
                logger.debug("target is awake, ignoring sending break")
                self.wakeup_event.clear()
                return
            # Wake up target
            self.com.break_condition = True
            if not self.wakeup_event.wait(0.5):
                raise Exception("Wakeup TIMEOUT")
            self.com.break_condition = False
            self.wakeup_event.clear()
        return

    def flushrx(self):
        n = self.com.in_waiting
        self.com.reset_input_buffer()
        return n

    def read(self, n):
        return self.com.read(n)

    def write(self, buf):
        return self.com.write(buf)

    def __str__(self):
        return "{} @ {:_d}".format(self.path, self.speed)


class Gpiodev:
    """
    GPIO for
    - suspend / wakeup
    - irqack
    """

    def __init__(self, config: GpioConfig):
        self.config = config
        self.edge = GPIO.RISING
        self.irq_event = Event()
        self.irq_count = 0
        self.dev = None

    def cleanup(self):
        GPIO.cleanup()

    def setup(self, dev):
        self.dev = dev
        atexit.register(self.cleanup)

        # GPIO numbering mode
        GPIO.setmode(GPIO.BCM)

        # input
        if True:
            GPIO.setup(self.config.host_irq_pin, GPIO.IN)
        else:
            if self.config.wakeup_level == 1:
                GPIO.setup(self.config.host_irq_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            if self.config.wakeup_level == 0:
                GPIO.setup(self.config.host_irq_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # output
        GPIO.setup(self.config.host_wakeup_pin, GPIO.OUT)
        self.wakeup_deasserted()

    def irq_callback(self):
        self.irq_count += 1
        self.irq_event.set()

    def wait_irq(self, send_irqack_fn):
        t0 = time.time()
        self.irq_event.wait()
        logging.debug(f'wait_irq {(time.time() - t0)*1000:1.3f}ms')
        if self.config.irq_mode == 1:
            send_irqack_fn()

    def wakeup_asserted(self):
        GPIO.output(self.config.host_wakeup_pin, self.config.wakeup_level == 1)

    def wakeup_deasserted(self):
        GPIO.output(self.config.host_wakeup_pin, self.config.wakeup_level == 0)


class GpioIrq(threading.Thread):
    """
    Watch GPIO irq_pin and trigger self.irq_callback()
    """

    def __init__(self, config: GpioConfig, irq_callback=lambda: None):
        super().__init__()
        self.name = 'GPIO_IRQ'
        self.setDaemon(True)
        self.config = config
        self.irq_callback = irq_callback
        self.edge = None
        self.loop = True
        self.enabled = False

    def reset_edge(self):
        if GPIO.input(self.config.host_irq_pin) == 0:
            self.edge = GPIO.RISING
        else:
            self.edge = GPIO.FALLING

    def run(self):
        state_table = {
                (1, GPIO.RISING) : (GPIO.FALLING, True),
                (1, GPIO.FALLING) : (GPIO.RISING, False),
                (2, GPIO.RISING) : (GPIO.FALLING, True),
                (2, GPIO.FALLING) : (GPIO.RISING, True),
        }
        edge_invert = {
            GPIO.RISING: GPIO.FALLING,
            GPIO.FALLING: GPIO.RISING,
        }
        edge_names = {
            GPIO.RISING: 'RISING',
            GPIO.FALLING: 'FALLING',
        }
        if self.config.irq_mode == 1:
            self.edge = GPIO.RISING
        else:
            self.reset_edge()
        while self.loop:
            GPIO.wait_for_edge(self.config.host_irq_pin, self.edge)
            name = edge_names.get(self.edge, '')
            key = (self.config.irq_mode, self.edge)
            self.edge, trigger = state_table.get(key, (edge_invert[self.edge], False))
            logging.debug(('GPIO_IRQ', name, 'TRIG' if trigger else ''))
            if trigger:
                self.irq_callback()
                # only enable after we have seen the first trigger
                self.enabled = True


def spidev_check():
    if 'SpiDev' not in globals():
        raise NotImplementedError(
            '''

        The spidev module required to use SPI transport is missing.
        You may be able to install this with a command like
        "pip3 install --user spidev"

        '''
        )


class Spidev(HIO):
    STATUS_FIFO     = 2**0
    STATUS_UNDERRUN = 2**1
    STATUS_OVERRUN  = 2**2

    def __init__(self, uri, speed=1e6, **kwargs):
        spidev_check()
        super().__init__(path=uri, speed=speed, **kwargs)
        self.name = 'HIO:Spidev'
        self.gpio: Gpiodev = False
        match = re.fullmatch('spidev(?:(\d)\.(\d))?', uri)
        if not match:
            raise Exception("Bad spidev URI")
        devno = int(match.group(1)) if match.group(1) else 0
        cs = int(match.group(2)) if match.group(2) else 0
        self.uri = 'spidev{}.{}'.format(devno, cs)
        self.spi_controller = SpiDev()
        self.spi_controller.open(devno, cs)
        self.spi_controller.max_speed_hz = int(speed)

    def start(self):
        super().start()

    def set_timeout(self, timeout):
        # timeout doesn't make much sense on SPI
        return None

    def target_sleep(self):
        if self.suspend_enabled:
            # Can't use call_async since that will do wakeup
            self.wakeup_event.clear()
            self.writemsg(Message(hio.api.sys.sleep, 'req').pack(0))

    def irqack(self):
        self.writemsg(Message(hio.api.sys.irqack, 'req').pack(0))

    def target_wakeup(self):
        if not self.suspend_enabled:
            return

        if self.gpio:
            self.gpio.wakeup_asserted()
        if not self.wakeup_event.wait(1.5):
            raise Exception("Wakeup TIMEOUT")
        if self.gpio:
            self.gpio.wakeup_deasserted()

    def status(self):
        data = self.spi_controller.xfer3(b'SS')
        return data[1]

    def wait_status(self, mask, value):
        if self.gpio_irq.enabled:
            self.gpio.wait_irq(self.irqack)
        t0 = time.time()
        while True:
            s = self.status()
            if s != 0xff and (s & mask) == value:
                break
        logging.debug(f'wait_status {s:03b}b exit {(time.time() - t0)*1000:1.3f}ms')
        return

    def config_gpio(self, enable=True):
        # TODO: move to HIO
        if enable:
            self.irq_enabled = self.gpio.config.irq_mode != 0
            rsp = self.call(hio.api.sys.config,
                            self.gpio.config.wakeup_pin,
                            self.gpio.config.wakeup_level,
                            self.gpio.config.irq_pin,
                            self.gpio.config.irq_mode)
            # GPIO_0 technically exists but here it is considered as disabled
            # GPIO_0 is CLK in SPI mode
            self.suspend_enabled = self.gpio.config.wakeup_pin != 0
        else:
            self.suspend_enabled = False
            self.irq_enabled = False
            rsp = self.call(hio.api.sys.config, 0, 0, 0, 0)
        return rsp.status == 0

    def enable_suspend(self, enable=True):
        if enable:
            self.config_gpio(True)
            if self.suspend_enabled:
                self.target_sleep()
        else:
            if self.suspend_enabled:
                self.target_wakeup()
            self.config_gpio(False)

    def read(self, length):
        self.wait_status(self.STATUS_FIFO, self.STATUS_FIFO)
        return bytes(self.spi_controller.xfer3(b'T' + bytes(length))[1:])

    def write(self, buf):
        self.spi_controller.xfer3(b'R' + buf)

    def reset(self):
        self.spi_controller.xfer3(b'kiLl')

    def __str__(self):
        return "{} @ {:_d}".format(self.uri, self.speed)


class FtdiSPI(HIO):
    MAXSIZE = 1023 # max usb chunk size, this number is picked
                   # from a hat, but probably have to be less than infinity
    STATUS_FIFO     = 2**0
    STATUS_UNDERRUN = 2**1
    STATUS_OVERRUN  = 2**2

    def __init__(self, uri, speed=1e6, **kwargs):
        if 'SpiController' not in globals():
            msg = '''
The PyFtdi module required to use FtdiSPI transport is missing.
You may be able to install this with a command like
    "pip3 install --user pyftdi"
'''
            raise NotImplementedError(msg)

        if uri == 'ftdi':
            uri = 'ftdi://ftdi:ft4232h/2'
            pass
        super().__init__(path=uri, speed=int(speed), **kwargs)
        self.name = 'HIO:FtdiSPI'
        self.spi_controller = SpiController()
        self.spi_controller.configure(uri)
        self.device = self.spi_controller.get_port(cs=0, freq=self.speed, mode=0)
        self.outq = deque()
        self.start()
        pass

    def wakeup(self, enable):
        return

    def status(self):
        data = self.device.exchange(b'SS', duplex=True)
        return data[1]

    def set_timeout(self, timeout):
        # timeout doesn't make much sense on SPI
        return None

    def wait_status(self, mask, value):
        while True:
            s = self.status()
            if s != 0xff and (s & mask) == value:
                break
            if self.outq:
                self.__write(self.outq.popleft())
            pass
        return

    def read(self, length):
        if not self.raw:
            # need to loop here to avoid usb size limits
            self.wait_status(self.STATUS_FIFO, self.STATUS_FIFO)
        remain = length
        n = min(remain, self.MAXSIZE)
        data = self.device.exchange(b'T', readlen=1+n, stop=(n==remain), duplex=True)
        del data[0] # initial T
        remain -= n
        while remain > 0:
            n = min(remain, self.MAXSIZE)
            data.extend(self.device.read(n, start=False, stop=(n==remain)))
            remain -= n
            pass
        return bytes(data)

    def write(self, buf):
        if self.raw:
            self.__write(buf)
        else:
            self.outq.append(buf)
        return len(buf)

    def __write(self, buf):
        offset = 0
        remain = len(buf)
        n = min(remain, self.MAXSIZE)
        self.device.write(b'R' + buf[offset:offset+n], start=True, stop=(n==remain))
        offset += n
        remain -= n
        while remain > 0:
            n = min(remain, self.MAXSIZE)
            self.device.write(buf[offset:offset+n], start=False, stop=(n==remain))
            offset += n
            remain -= n
            pass
        return offset

    def reset(self):
        self.device.write(b'kiLl')

    def __str__(self):
        return "{} @ {:_d}".format(self.path, self.speed)
    pass


def update_config_suspend(config, **kwargs):
    if not kwargs.get('suspend', False):
        config.wakeup_pin = 0
    return config


def update_config_irq(config, **kwargs):
    irq = kwargs.get('irq', 0)
    if irq == 0:
        config.irq_mode = 0
        config.irq_pin = 0
    else:
        if irq not in (0, 1, 2):
            print(f'invalid irq mode {irq}')
            sys.exit(1)
        config.irq_mode = irq
    return config


def update_config(config, **kwargs):
    config = update_config_suspend(config, **kwargs)
    config = update_config_irq(config, **kwargs)
    return config


def open_spidev(path, **kwargs):
    dev = Spidev(path, **kwargs)

    config = update_config(RpiGpioConfig(), **kwargs)
    logger.info(config)

    dev.gpio = Gpiodev(config)
    dev.gpio.setup(dev)

    dev.gpio_irq = GpioIrq(config, dev.gpio.irq_callback)

    dev.gpio_irq.start()
    dev.start()
    return dev


def open(path, **kwargs):
    dev = None
    try:
        if path.startswith("/dev/"):
            dev = Serial(path, **kwargs)
        elif path.startswith("ftdi"):
            # FT4232H has MPSSE only on interface 1 and 2

            # ftdi URL on interface 3 or 4: use pyftdi uart
            if re.fullmatch(r"ftdi://[^/]*/[34]", path):
                dev = Serial(path, **kwargs)
            else:
                dev = FtdiSPI(path, **kwargs)
        elif path.startswith("spidev"):
            dev = open_spidev(path, **kwargs)
        elif path.startswith("COM"):
            dev = Serial(path, **kwargs)
        elif os.path.exists(path):
            dev = Socket(path, socket.AF_UNIX, **kwargs)
        elif ':' in path:
            dev = Socket(path, socket.AF_INET, **kwargs)
    except NotImplementedError as e:
        print(str(e))
    if not kwargs.get('raw', False):
        rsp = dev.call(hio.api.sys.query, timeout=1.0)
        if rsp is None:
            print("Failed to query hio.maxsize")
            dev.close()
            return None
        elif rsp.status == 0:
            dev.hiomaxsize = rsp.maxsize
    return dev
