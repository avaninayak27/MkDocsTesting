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

import sys
import socket
import io
import threading
import time
import serial
import argparse


class Console(threading.Thread):
    @classmethod
    def add_arguments(cls, main):
        con = main.add_argument_group(title='Console options')
        con.add_argument('--console-host', metavar='HOSTNAME',
                         default=argparse.SUPPRESS,
                         help='Host for console terminal server')
        con.add_argument('--console-port', metavar='PORT',
                         default=4000,
                         help='Port for console terminal server [default=%(default)u]')
        con.add_argument('--console-device', metavar='DEVICE',
                         default=argparse.SUPPRESS,
                         help='Device file for UART based console.')
        con.add_argument('--console-speed', metavar='SPEED',
                         default=2456700,
                         help='Baudrate for UART based console [default=%(default)u].')
        con.add_argument('--noconsole', action='store_true',
                         default=argparse.SUPPRESS,
                         help='Do not attach to debug console')
        con.add_argument('--console-logfile', metavar='FILENAME',
                         help='File to append console output to')
        return

    @classmethod
    def factory(cls, *args, **kw):
        cclass = None
        cargs = []
        ckwargs = {}
        options = kw.get('options', None)
        if options is not None:
            if 'console_logfile' in options:
                ckwargs['logfile'] = options.console_logfile
            if 'noconsole' in options:
                cclass = NoConsole
            elif 'console_device' in options:
                cclass = UartConsole
                ckwargs['device'] = options.console_device
                ckwargs['baudrate'] = options.console_speed
            elif 'console_host' in options or 'host' in options:
                cclass = SocketConsole
                ckwargs['host'] = options.console_host \
                                  if 'console_host' in options else\
                                     options.host
                if 'console_port' in options:
                    ckwargs['port'] = options.console_port
        elif 'device' in kw:
            cclass = UartConsole
            cargs = args
            ckwargs = kw
        elif 'host' in kw:
            cclass = SocketConsole
            cargs = args
            ckwargs = kw
            pass

        if cclass is None:
            raise NotImplementedError("unknown arguments")

        return cclass(*cargs, **ckwargs)

    def __init__(self, logfile=None, **kw):
        super().__init__()
        self.daemon = True
        self.triggers = []
        self.output = []
        self.buffer = io.StringIO()
        if logfile:
            self.logfile = open(logfile, 'a')
            print('========== {} =========='.format(time.ctime()),
                  file=self.logfile)
            self.logfile.flush()
        else:
            self.logfile = None


    def add_trigger(self, callobj, regexp):
        self.triggers.append((callobj, regexp))

    def run_notrigger(self):
        while True:
            b = self.read(1024)
            d = b.decode('utf-8', 'replace')
            sys.stdout.write(d)
            sys.stdout.flush()
            if self.logfile:
                self.logfile.write(d)
                self.logfile.flush()
        pass

    def run(self):
        if not self.triggers:
            return self.run_notrigger()
        while True:
            b = self.readline().rstrip()
            consumed = False
            for fn, regexp in self.triggers:
                match = regexp.match(b)
                if match:
                    consumed = fn(match)
                    break
            if not consumed:
                print(b)
    def read(self, amount):
        raise NotImplementedError('read not implemented')

    def readline(self):
        while '\n' not in self.buffer.getvalue():
            self.buffer.write(self.read(256).decode('utf-8', 'remove'))
        return self.buffer.readline()

class NoConsole(Console):
    def __init__(self, *args, **kw):
        super().__init__(**kw)
        self.start()

    def run(self):
        while True: time.sleep(1)
        return


class UartConsole(Console):
    def __init__(self, device, baudrate=2457600, **kw):
        super().__init__(**kw)
        self.serial = serial.Serial(device, baudrate, timeout=0.1)
        self.start()

    def read(self, amount):
        return self.serial.read(amount)

class SocketConsole(Console):
    def __init__(self, host, port=4000, **kw):
        print(host, port)
        for ai in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
            try:
                sock = socket.socket(family=ai[0], type=ai[1], proto=ai[2])
                sock.connect(ai[4])
            except (OSError, TimeoutError):
                continue
            break
        else:
            raise RuntimeError('failed to connect to {}'.format(host))
        super().__init__(**kw)
        self.sock = sock
        self.start()

    def read(self, amount):
        return self.sock.recv(amount)


def main():
    from argparse import ArgumentParser, SUPPRESS
    ap = ArgumentParser()

    ap.add_argument('console_host', metavar='hostname', nargs='?', default=SUPPRESS)
    ap.add_argument('console_port', metavar='port', default=SUPPRESS, nargs='?')

    Console.add_arguments(ap)

    op = ap.parse_args()
    c = Console.factory(options=op)
    try:
        while True:
            input('')
    except KeyboardInterrupt:
        raise SystemExit(0)


if __name__ == '__main__':
    main()
