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
Given a HOST with running OpenOCD and uart relay,

connects to HOST and load/boot an ELF image.


Ex

./script/gdbrun.py apps/helloworld.elf --noconsole --nowait
"""
import sys, time
import struct
import gdbremote
import argparse
import console
# from regbase import Register
# import regdef
# import testcase
import bits.bootargs

def get_parser():
    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument('--host', default='localhost', help='Host for OpenOCD and console terminal server')
    arg.add_argument('--gdb-port', default=3333, type=int, help='GDB remote protocol port')
    arg.add_argument('--timeout', type=int, default=3600, help='Timeout in seconds for app to complete')
    arg.add_argument('--nowait', action='store_true', help='Do not wait for application to terminate')
    arg.add_argument('--noread', action='store_true', help='Do not read trace after target stopped')
    arg.add_argument('--trace', const=0x00003f0000000000001fffff, nargs='?', type=lambda x:int(x,0), help='Enable on-chip trace circuitry.')
    arg.add_argument('--symbol', default='main',
                     help='symbol to start trace at (default %(default)r)')
    arg.add_argument('--gpio-mux', default=0x90, nargs='?', type=lambda x:int(x,0), help='Set gpio mux configuration.')
    arg.add_argument('--power-on-reset', action='store_true', help='Start ROM from reset')
    arg.add_argument('--por', dest='power_on_reset', action='store_true', help=argparse.SUPPRESS) #alias for above
    arg.add_argument('--rom', dest='power_on_reset', action='store_true', help=argparse.SUPPRESS) #alias for above
    arg.add_argument('--puf-seed', default=None, help='Seed for filling puf RAM, needed on FPGA')
    # testcase.add_testcase_argument(arg, True)
    arg.add_argument('--image', help='Image in .elf format to be loaded and run')
    arg.add_argument('--serial', type=str, default="", help='device serial number')
    arg.add_argument('--app_elf', type=str, default="", help='Application image elf file')
    arg.add_argument('--app_addr', type=str, default="0x00", help='Application image flash address')
    arg.add_argument('--dev_conf', type=str, default="", help='Configuration .json file')
    arg.add_argument('--fs_img', type=str, default="", help='Filesystem image .img file to write')
    arg.add_argument('--fs_addr', type=str, default=0x5FF000, help='Filesystem image start address to write')
    arg.add_argument('--out_img', type=str, default="", help='output image .img file for read')
    arg.add_argument('--read_addr', type=str, default=0x5FF000, help='Flash start address to read')
    arg.add_argument('--read_size', type=str, default=0x200000, help='Size to read')
    arg.add_argument('--clear_flash', action='store_true', help='Flag to perform Clear flash')
    arg.add_argument('--output', type=str, default="", help='Application image bin file output path')
    arg.add_argument('--tfm_app', type=str, default="", help='TFM application image elf/bin file')
    arg.add_argument('--ns_app_image_offset', type=str, default=0x400000, help='Non-secured application image offset address')
    arg.add_argument('--no_gdb_reset', action='store_true', help='Flag to not perform gdb reset using SWD during Clear flash/Prog Flash action')
    arg.add_argument('--npu_img', type=str, default="", help='NPU Application image (.bin) file to write')
    arg.add_argument('--npu_addr', type=str, default=0x00280000, help='NPU Application image start address to write. Default: 0x00280000') #
    arg.add_argument('--boot_arg', type=str, default="", help='Boot argument string (space-separated), e.g., "hio.baudrate=921600 hio.maxsize=1600"') #
    arg.add_argument('--bootarg_addr', type=str, default=0x00200000, help='Boot arguments start address to write. Default: 0x00200000') #
    arg.add_argument('--reset_device', action='store_true', help='Flag to perform device reset')
    return arg
    

def enable_serdes(gdb):
    global afe, core, support

    # Enable ck40_fpga
    core.top.freq_sel[2]  = 3
    gpio.amux            |= 4

    # Innotrace registers
    support.innotrace.phy.fend.ed_gated = 0
    support.innotrace.halt_en           = 0
    support.hsl.format                  = 1 if version.impl == 0 else 0

    # Enable serdes TX
    core.serdes.mux           = 0
    core.serdes.load_delay_tx = 2
    core.serdes.loopback_en   = 0
    core.serdes.rx_en         = 0
    core.serdes.tx_en         = 3
    core.serdes.lvds.pd.tx_0  = 0
    core.serdes.lvds.pd.tx_1  = 0

    # Enable 640MHz for serdes hsl
    afe.rfa.rxtdc.clock.en_ck_640m_dig = 1

def trace_enable(gdb, mask):
    global support, gpio, rst_clk, frontend
    gdb.monitor_cmd('spb567_trace stop')
    gdb.write32(0xe000edfc, 2**24)
    mask, value = divmod(mask, 2**32)
    gdb.write32(support.innotrace.mac.enable._addr, value)
    print("mac.it_enable = {:08x}".format(value))
    mask, value = divmod(mask, 2**32)
    gdb.write32(support.innotrace.phy.enable._addr, value)
    if value & 1:
        # To get ADC samples we need to set another enable and the SDL clock
        rst_clk.rstclk.set = 0x10001 << 11
    print("phy.it_enable = {:08x}".format(value))
    mask, value = divmod(mask, 2**32)
    gpio.trace_mask = value
    print("gpio.trace_mask = {:08x}".format(value))
    gdb.monitor_cmd('spb567_trace start')
    return

def main(img_file, nowait, gdb_port, bulk_erase = False, no_gdb_reset = False):
    global version
    err_msg = ""
    try:
        arg = get_parser()
        
        console.Console.add_arguments(arg)
        bits.bootargs.BootArguments.add_arguments(arg)
        opt = arg.parse_args()
        opt.image = img_file
        opt.nowait = nowait
        opt.noconsole = True
        opt.gdb_port = gdb_port
        err_msg = ""
        # print("completed gdbrun 1")
        try:
            console1 = console.Console.factory(options=opt)
        except Exception as e:
            print("Failed to open console: {}".format(str(e)))
            raise Exception("Failed to open console: {}".format(str(e)))
        
        gdb  = gdbremote.GDBclient()
        # print("completed gdbrun 2")
        try:
            gdb.connect(opt.host, opt.gdb_port)

            if no_gdb_reset:
                gdb.monitor_cmd("halt")
            else:
                # gdb.monitor_cmd("reset halt")
                gdb.monitor_cmd("halt")
            
            time.sleep(0.1)
            gdb.monitor_cmd("mww 0xE000E000 0x1") #set $primask = 0x1
            gdb.monitor_cmd("mww 0x40005060 0x0") #set *0x40005060 = 0x0

            entry = gdb.load(opt.image)
            args = bits.bootargs.BootArgumentsELF(opt.image)
            # for k, v in kwargs.items():
            #     args.add(f"{k}={v}")
            argc, argv = gdb.bootargs(args)
            gdb.set_reg(0, argc)
            gdb.set_reg(1, argv)
            gdb.set_reg(15, entry)
            gdb.cont()
            # if "erase" in opt.image:
            #     # print("Print start waiting for 20 sec")
            #     time.sleep(10)
            # print("Print wauting for 20 sec")
            gdb.disconnect()
            
        except Exception as e:
            err_msg = str(e)
        finally:
            try:
                gdb.disconnect()
                time.sleep(0.5)
            except:
                pass

        return err_msg
        
    except Exception as e:
        err_msg = str(e)
    
    finally:
        # Register._finalized = False
        return err_msg

def gdb_device_reset(img_file, nowait, gdb_port):
    global version
    err_msg = ""
    try:
        arg = get_parser()
        
        # console.Console.add_arguments(arg)
        # bits.bootargs.BootArguments.add_arguments(arg)
        opt = arg.parse_args()
        opt.image = img_file
        opt.nowait = nowait
        opt.noconsole = True
        opt.gdb_port = gdb_port
        err_msg = ""
        # print("completed gdbrun 1")
        # try:
        #     console1 = console.Console.factory(options=opt)
        # except Exception as e:
        #     print("Failed to open console: {}".format(str(e)))
        #     raise Exception("Failed to open console: {}".format(str(e)))

        gdb  = gdbremote.GDBclient()

        try:
            gdb.connect(opt.host, opt.gdb_port)

            gdb.monitor_cmd("halt")
            time.sleep(0.1)
            gdb.monitor_cmd("mww 0xE000E000 0x1") #set $primask = 0x1
            gdb.monitor_cmd("mww 0x40005060 0x0") #set *0x40005060 = 0x0
            time.sleep(0.1)
            gdb.monitor_cmd("reset")
            gdb.disconnect()
            
        except Exception as e:
            err_msg = str(e)
        finally:
            try:
                gdb.disconnect()
                time.sleep(0.1)
            except:
                pass

        return err_msg
        
    except Exception as e:
        err_msg = str(e)
    
    finally:
        # Register._finalized = False
        return err_msg
    
if __name__ == '__main__':
    arg = get_parser()
    opt = arg.parse_args()

    img_file = opt.image
    gdb_port = opt.gdb_port
    main(img_file, True, gdb_port)
