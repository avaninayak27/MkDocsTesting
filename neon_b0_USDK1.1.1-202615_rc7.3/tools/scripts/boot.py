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

import os
import sys
import time
import argparse
from sys import platform
import shlex, subprocess
import signal
import socket
import arden, gdbrun, gdb_multiarch_erase

import hostio
import hio.base, hio.api.sys
import bits.flash
import flash as flasher
import psutil
from sys import platform as os_platform

from constants import *

import json
import update_dev_conf

import signal, psutil
from func_timeout import func_timeout
from func_timeout.exceptions import FunctionTimedOut
from pyftdi.usbtools import UsbTools
import shutil

try:
    from bootgui.resources.paths import SDK_FILES, GORDON_SWD, GORDON_ERASE
except:
    pass

WIN_OPENOCD_EXE = ""
if platform == "win32":
    try:
        from bootgui.resources.paths import WIN_OPENOCD_EXE
    except:
        try:
            WIN_OPENOCD_EXE = shutil.which("openocd.exe")
            # print("WIN_OPENOCD_EXE: ", WIN_OPENOCD_EXE)
        except:
            pass

    if WIN_OPENOCD_EXE == "":
        print("openocd.exe not found in the system PATH.")
        print("Please download it from:")
        print("https://github.com/xpack-dev-tools/openocd-xpack/releases/download/v0.10.0-15/xpack-openocd-0.10.0-15-win32-x64.zip")
        print("Extract the archive and add the FULL path of the following bin directory to your PATH environment variable:")
        print("Example: C:\\Users\\YourUser\\Downloads\\xpack-openocd-0.10.0-15-win32-x64\\xpack-openocd-0.10.0-15\\bin")
        sys.exit(1)

class swdError(Exception):
    pass

class FlashError(Exception):
    pass

class swd_flasher_hio_server():
    def __init__(self, ocd="OpenOCD", interface='ftdi_swd_serial', adapter_serial=None, host='localhost', partition=None, length=0x00, bulk_erase = False, hio_server_port = 10000, gang_program = False, clear_flash = False, no_gdb_reset = False, reset_device = False):
        # super().__init__(ocd, interface, adapter_serial, host, partition, length)
        self.ocd = ocd
        self.interface = interface
        self.adapter_serial = adapter_serial
        self.host = host
        self.gdb_port = 3333 #gdb_port
        self.tcl_port = 6666
        self.telnet_port = 6667
        self.partition = partition
        # self.image = image
        # self.flashaddress = flashaddress
        self.length = length
        self.ocd_connection = None
        # print( "adapter_serial = ", adapter_serial)

        self.tflash = None
        self.bulk_erase = bulk_erase
        self.hio_server_port = hio_server_port
        self.host = host
        self.gang_program = gang_program
        self.clear_flash = clear_flash
        self.no_gdb_reset = no_gdb_reset
        self.reset_device = reset_device
        # print("clear flash is ", self.clear_flash)
        self.tflasher_err = ""

        self.run_app = False      # default: Flash application
        self.app_elf = None       # path to the ELF to run in RAM

        if platform == "win32":
            kill_process("openocd.exe")
        else:
            kill_process("openocd")
        time.sleep(0.1)

    def get_ports(self):
        # print("Entered to get port")
        autoport = True
        time_out = 10
        ocdserverport = self.tcl_port #6666 #tcl port
        if(autoport == True):
            port_selected = False
            while(port_selected == False):
                try:
                    try:
                        result = func_timeout(time_out, check_port_number, args=("", ocdserverport))
                        
                        if result == 0:
                            self.tcl_port = ocdserverport
                            print("Using port " + str(ocdserverport) + " for ocdserver")
                            port_selected = True
                        else:
                            ocdserverport+=1
                        
                    except FunctionTimedOut as e:
                        # print("Exception occurred", str(e))
                        self.tcl_port = ocdserverport
                        print("Using port " + str(ocdserverport) + " for ocdserver")
                        port_selected = True

                except Exception as e:
                    # print('Failed to get ocdserverport: ' + str(e))
                    raise swdError('Failed to get ocdserverport: ' + str(e))
                    
                except:
                    # print('Failed to get ocdserverport' + " with unknown error.")
                    raise swdError('Failed to get ocdserverport' + " with unknown error.")

        telnet_port = ocdserverport + 1 #telnet port
        if(autoport == True):
            port_selected = False
            while(port_selected == False):
                try:
                    try:
                        result = func_timeout(time_out, check_port_number, args=("", telnet_port))
                        
                        if result == 0:
                            self.telnet_port = telnet_port
                            print("Using port " + str(telnet_port) + " for telnet")
                            port_selected = True
                        else:
                            telnet_port+=1
                        
                    except FunctionTimedOut as e:
                        self.telnet_port = telnet_port
                        print("Using port " + str(telnet_port) + " for telnet")
                        port_selected = True
                        
                except Exception as e:
                    # print('Failed to get telnet_port: ' + str(e))
                    raise swdError('Failed to get telnet_port: ' + str(e))
                    
                except:
                    # print('Failed to get telnet_port' + " with unknown error.")
                    raise swdError('Failed to get telnet_port' + " with unknown error.")

        gdb_port = self.gdb_port #gbd port
        if(autoport == True):
            port_selected = False
            while(port_selected == False):
                try:
                    try:
                        result = func_timeout(time_out, check_port_number, args=("", gdb_port))
                        if result == 0:
                            self.gdb_port = gdb_port
                            print("Using port " + str(gdb_port) + " for GDB")
                            port_selected = True
                        else:
                            gdb_port+=1
                        
                    except FunctionTimedOut as e:
                        self.gdb_port = gdb_port
                        print("Using port " + str(gdb_port) + " for GDB")
                        port_selected = True
                        
                except Exception as e:
                    # print('Failed to get gdb_port: ' + str(e))
                    raise swdError('Failed to get gdb_port: ' + str(e))
                    
                except:
                    # print('Failed to get gdb_port' + " with unknown error.")
                    raise swdError('Failed to get gdb_port' + " with unknown error.")

    def initial_setup(self):
        # start_t = time.time()
        self.get_ports()
        # print("execution time for get_ports:", time.time() - start_t)
        
        self.p=None
        ocd_extra_cmd=""
        openocd_cmd = ""
        if(self.ocd == 'OpenOCD'):
            try:
                if(self.interface == 'cmsis-dap'):
                    interface_config_file = OPENOCD_CMSIS_CFG
                    t2_config_file = "t3a_ftdi_swd.cfg"
                elif(self.interface == 'ftdi_swd'):
                    interface_config_file = "ftdi_swd.cfg"
                    t2_config_file = "t3a_ftdi_swd.cfg"
                elif(self.interface == 'ftdi_swd_serial'):
                    interface_config_file = "inp3000_swd.cfg" #"ftdi_swd_serial.cfg"
                    t2_config_file = "t3a_ftdi_swd.cfg"
                    interface_serial = str(self.adapter_serial)
                    # print("interface_serial = ", interface_serial)
                    ocd_extra_cmd = " -c \'set FTDI_SERIAL " + interface_serial + "\'"
                elif(self.interface == 'ftdi_jtag'):
                    interface_config_file = "ftdi.cfg"
                    t2_config_file = "t2.cfg"
                elif(self.interface == 'ftdi_jtag_serial'):
                    interface_config_file = "ftdi.cfg"
                    t2_config_file = "t3a_ftdi_swd.cfg"
                    interface_serial = str(self.adapter_serial)
                    ocd_extra_cmd = " -c \'set FTDI_SERIAL " + interface_serial + "\'"
                elif(self.interface == 'jlink'):
                    interface_config_file = OPENOCD_JLINK_CFG
                    t2_config_file = "t3a_ftdi_swd.cfg"
                
                #-c 'tcl_port 6666' -c 'telnet_port 6667' -c 'gdb_port 3333'
                ocd_extra_cmd = ocd_extra_cmd + " -c 'tcl_port " + str(self.tcl_port) + "' -c 'telnet_port " + str(self.telnet_port) + "' -c 'gdb_port " + str(self.gdb_port) + "'"
                
                log_cmd = " -l openocd_log"
                # print("Starting OpenOCD")
                if platform == "linux" or platform == "linux2":
                    # kill_process("openocd.exe")
                    OPENOCD_LINUXARM = "openocd"
                    if(os.uname()[4][:3] == 'arm'):
                        # if(ocd_extra_cmd != None):
                        openocd_cmd = "\"" + OPENOCD_LINUXARM + "\"" + log_cmd + " -s " + "\"" +  SDK_FILES + "\"" + ocd_extra_cmd + " -f " + interface_config_file + " -f " + t2_config_file
                        # else:
                        #     openocd_cmd = OPENOCD_LINUXARM + log_cmd + " -s " +  SDK_FILES + " -f " + interface_config_file + " -f " + t2_config_file
                        # print("openocd_cmd:", openocd_cmd)

                    else:
                        OPENOCD_LINUX64 = "openocd"
                        # if(ocd_extra_cmd != None):
                        openocd_cmd = "\"" + OPENOCD_LINUX64 + "\"" + log_cmd + " -s " + "\"" +  SDK_FILES + "\"" + ocd_extra_cmd + " -f " + interface_config_file + " -f " + t2_config_file
                        # else:
                        #     openocd_cmd = OPENOCD_LINUX64 + log_cmd + " -s " +  SDK_FILES + " -f " + interface_config_file + " -f " + t2_config_file
                        # print("openocd_cmd:", openocd_cmd)
                        
                elif platform == "darwin":
                    print("OSX detected! Platform is currently not supported")
                elif platform == "win32":
                    # kill_process("openocd.exe")
                    # print("starting win32 openocd")
                    # if(ocd_extra_cmd != None):
                    openocd_cmd = "\"" + WIN_OPENOCD_EXE + "\"" + log_cmd + " -s " + "\"" +  SDK_FILES + "\"" + ocd_extra_cmd + " -f " + interface_config_file + " -f " + t2_config_file
                    # else:
                    #     openocd_cmd = WIN_OPENOCD_EXE + log_cmd + " -s " +  SDK_FILES + " -f " + interface_config_file + " -f " + t2_config_file
                    
                    openocd_cmd = openocd_cmd.replace("'", "\"")
                    # print("Command for openocd start: ", openocd_cmd)
                    
            except Exception as e:
                # print("\tERROR: Failed to start OpenOCD")
                # print(e)
                openocd_cmd = ""
                raise swdError('Failed to start OpenOCD: ' + str(e))
                # return 'Failed to start OpenOCD'
                # sys.exit(1)
        
        if openocd_cmd:
            #below to update the reset.py location on config file
            file_chng = os.path.join(SDK_FILES,t2_config_file)
            script_path = os.path.dirname(os.path.abspath(__file__))
            # print("script_path =", script_path)
            reset_file = os.path.join(script_path, 'reset.py')
            if platform == "win32":
                reset_file = reset_file.replace("\\", "\\\\")
                replace_str = "exec python " + reset_file + f" --serial {self.adapter_serial}"
            else:
                replace_str = "exec python3 " + reset_file + f" --serial {self.adapter_serial}"
            # print("replace cfg", file_chng, "reset.py", replace_str)
            replace_line_in_file(file_chng, "reset.py", replace_str)
            print(openocd_cmd)
            try:
                self.start_connection(openocd_cmd)
            except Exception as e:
                raise swdError('Failed to start OpenOCD: ' + str(e))
        
        return ""
    
    def start_connection(self, openocd_cmd):
        try:
            shlex.split(openocd_cmd)
            if 'linux' in os_platform.lower():
                setup_temp_files()
            que_num = que_for_openocd()
            # print("openocd_cmd: ", openocd_cmd)
            if self.gang_program:
                # self.p = subprocess.Popen(openocd_cmd, shell=True)
                # # self.p = subprocess.Popen(openocd_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                # # self.p = subprocess.Popen(openocd_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                # time.sleep(0.5) # give OpenOCD some time to start
                openocd_status = self.start_openocd(openocd_cmd, 1, 0.5)
                if not openocd_status:
                    raise swdError('OpenOCD not able to connect to device.')
            else:
                itr_cnt = 0
                while 1:
                    openocd_status = self.start_openocd(openocd_cmd)
                    if openocd_status:
                        break
                    itr_cnt = itr_cnt + 1
                    if itr_cnt > 2:
                        raise swdError('OpenOCD not able to connect to device.')

            que_for_openocd(mode="end", que_no = que_num)
        except Exception as e:
            raise swdError(str(e))
        
        if not self.reset_device:
            # print(" starting start_hio_server")
            try:
                #start hio server
                self.start_hio_server()
            except Exception as e:
                # print("exception at start_hio_server call", str(e))
                raise swdError(str(e))
            
    def start_openocd(self, openocd_cmd, wait_time1 = 0.5, wait_time2 = 0.5):
        
        if platform == "win32":
            openocd_cmd = openocd_cmd.replace("\\", "/")
            self.p = subprocess.Popen(openocd_cmd, shell=True)
            # self.p = subprocess.Popen(openocd_cmd, shell=True)
            time.sleep(0.2)

            if self.p.poll() is None:
                return True
            else:
                return False
                            
        elif platform == "linux" or platform == "linux2":

            try:

                self.p = subprocess.Popen(openocd_cmd, shell=True)
                
                cwd = os.getcwd()
                time.sleep(0.2)
                openocd_log = os.path.join(cwd, "openocd_log")
                
                for i in range(10):
                    log_stream = fp_follow(openocd_log)
                    if self.p.poll() is None:
                        openocd_err = get_openocd_error(log_stream, check_startup=True)
                        if openocd_err == 1:
                            # print("openocd started successfully")
                            return True
                        elif openocd_err == 0:
                            # print("openocd not started successfully")
                            return False
                    else:
                        # print("openocd not started successfully")
                        return False
                    time.sleep(0.2)
            # except Exception as e:
            #     print("Exception on start_openocd as", str(e))
            finally:
                pass

    def start_hio_server(self):
        cwd = os.getcwd()
        openocd_log = os.path.join(cwd, "openocd_log")
        print("openocd_log: ", openocd_log)
        if self.reset_device:
            try:
                device_reset(self.adapter_serial)
                # err_msg = gdbrun.gdb_device_reset("", True, self.gdb_port)

                if err_msg != "":
                    # print("Raising Exception at gdbrun.main call: ", err_msg)
                    raise Exception(err_msg)
                    # print("start_hio_server: start gdbrun.main. Error: = ", err_msg)

            except Exception as e:
                # print("Exception occured at start_hio_server clear flash", str(e))
                self.close_setup(reset_device = False)
                raise swdError(str(e))
            
        elif self.clear_flash:
            # print("Performing clear flash")
            
            log_stream = None
            try:
                
                for i in range(2):
                    # print("Clear flash: i=", str(i))
                    err_msg = ""
                    if i == 1:
                        # print("clear flash using gdb_multiarch_erase")
                        # gdb_multiarch_erase.run_gdb_commands(GORDON_ERASE, self.gdb_port, no_gdb_reset=self.no_gdb_reset)
                        err_msg = gdbrun.main(GORDON_ERASE, True, self.gdb_port, bulk_erase = self.bulk_erase, no_gdb_reset=self.no_gdb_reset)
                    else:
                        # print("general method of clear flash")
                        err_msg = gdbrun.main(GORDON_ERASE, True, self.gdb_port, bulk_erase = self.bulk_erase, no_gdb_reset=self.no_gdb_reset)
                    
                    if err_msg:
                        if os.path.isfile(openocd_log):
                            # print("File exists: ", openocd_log)
                            if log_stream is None:
                                log_stream = fp_follow(openocd_log)
                            openocd_err = get_openocd_error(log_stream)
                            # print("get_openocd_error: ", openocd_err)
                            if "clearing lockup after double fault" in openocd_err:
                                continue
                        else:
                            break
                    else:
                        if os.path.isfile(openocd_log):
                            # print("File exists: ", openocd_log)
                            if log_stream is None:
                                log_stream = fp_follow(openocd_log)
                            openocd_err = get_openocd_error(log_stream)
                            # print("get_openocd_error: ", openocd_err)
                            if "clearing lockup after double fault" in openocd_err:
                                if i == 0:
                                    continue
                                else:
                                    err_msg = "clearing lockup after double fault"

                            elif "cannot read IDR" in openocd_err:
                                err_msg = "Error: Error connecting DP: cannot read IDR"
                                break
                            
                            # elif "Warn : keep_alive() was not invoked" in openocd_err:
                            #     # err_msg = "Warn : keep_alive() was not invoked"
                            #     break
                            elif "success" in openocd_err:
                                err_msg = ""
                                break
                                # continue
                        else:
                            break
                        # else:
                        #     print("File not exists: ", openocd_log)
                
                if err_msg != "":
                    # print("Raising Exception at gdbrun.main call: ", err_msg)
                    raise Exception(err_msg)
                    # print("start_hio_server: start gdbrun.main. Error: = ", err_msg)

            except Exception as e:
                # print("Exception occured at start_hio_server clear flash", str(e))
                # self.close_setup()
                raise swdError(str(e))
        elif self.run_app and self.app_elf:
            print("Loading application into RAM")
            try:
                log_stream = None
                err_msg = ""

                print("Run-app mode: loading ELF via GDB:", self.app_elf)

                old_argv = sys.argv[:]
                sys.argv = [sys.argv[0]]
                # Load and run the given ELF via GDB (RAM execution)
                err_msg = gdbrun.main(self.app_elf, True, self.gdb_port, bulk_erase=self.bulk_erase)
                sys.argv = old_argv

                # If gdbrun did not report an error, still scan openocd_log for known issues
                if err_msg == "" and os.path.isfile(openocd_log):
                    log_stream = fp_follow(openocd_log)
                    openocd_err = get_openocd_error(log_stream)
                    # print("get_openocd_error (run mode): ", openocd_err)
                    if "clearing lockup after double fault" in openocd_err:
                        err_msg = "clearing lockup after double fault"
                    elif "cannot read IDR" in openocd_err:
                        err_msg = "Error: Error connecting DP: cannot read IDR"

                if err_msg != "":
                    raise Exception(err_msg)

            except Exception as e:
                # self.close_setup()
                raise swdError(str(e))
        else:
            # print("Enter to non clear flash")
            try:            
                print("arden.hio_server: server_port = ", self.hio_server_port, GORDON_SWD, self.tcl_port)
                self.hio_serv = arden.hio_server(GORDON_SWD, self.tcl_port, self.hio_server_port)
                self.hio_serv.start()
                
                while not self.hio_serv.startDone:
                    time.sleep(0.01)
                    if self.hio_serv.err_msg:
                        break
                
                if self.hio_serv.err_msg:
                    raise Exception(self.hio_serv.err_msg)
                    
                # ./script/gdbrun.py ./apps/gordon-jtag/bin/gordon-jtag.elf --noconsole --nowait
                err_msg = gdbrun.main(GORDON_SWD, True, self.gdb_port, bulk_erase = self.bulk_erase)

                if err_msg == "":
                    if os.path.isfile(openocd_log):
                        # print("File exists: ", openocd_log)
                        # with open(openocd_log, "r") as fp:
                        #     print(fp.read())
                        log_stream = fp_follow(openocd_log)
                        openocd_err = get_openocd_error(log_stream)
                        # print("get_openocd_error: ", openocd_err)
                        if "clearing lockup after double fault" in openocd_err:
                            err_msg = "clearing lockup after double fault"

                        elif "cannot read IDR" in openocd_err:
                            err_msg = "Error: Error connecting DP: cannot read IDR"

                    # else:
                    #     print("File not exists: ", openocd_log)
                
                if err_msg != "":
                    raise Exception(err_msg)
                    # print("start_hio_server: start gdbrun.main. Error: = ", err_msg)
                
                time.sleep(0.1)
                
                try:
                    self.create_tflash()
                except Exception as e:
                    self.tflasher_err = str(e)
                    raise Exception(str(e))

            except Exception as e:
                # self.close_setup()
                raise swdError(str(e))
                # print("Exception as start_hio_server: ", str(e))
    
    def create_tflash(self):
        try:

            device = self.host + ":" + str(self.hio_server_port) #'localhost:10000'
            speed = 921600
            self.dev = hostio.open(device, registry=hio.base.registry, speed=speed, sync=None)
            
            if not self.dev:
                raise Exception("dev not found")
                # sys.exit(1)
            self.dev.hiomaxsize = 4132
    
            rsp = self.dev.call(hio.api.sys.query)
            if rsp is None:
                # print('Flash helper is not responding, check your cables')
                raise Exception('Flash helper is not responding, check your cables')
                # sys.exit(1)
            if rsp.maxsize < 512+8:
                print('Message maxsize too small ({rsp.maxsize})')
                raise Exception('Message maxsize too small ({rsp.maxsize})')
                # sys.exit(1)
            # print("dev.hiomaxsize =" , rsp.maxsize)
    
            self.tflash = bits.flash.TargetFlash(self.dev)
        except Exception as e:
            self.tflash = None
            raise Exception(str(e))
            # print("Exception occurred during the create_tflash", str(e))
    
    def close_setup(self, reset_device = True):

        try:
            self.tflash.close()
            self.dev.close()
        except:
            pass
        self.tflash = None
        try:
            if not self.hio_serv.terminate_success:
                self.hio_serv.terminate()
        except Exception as e:
            pass
            # print("Exception occured at close_setup: ", str(e))

        try:
            # kill_process("openocd")
            if(self.p != None):
                # print("Terminating openocd pocess")
                kill_child_processes(self.p.pid)
                # if platform == "linux" or platform == "linux2":
                #     self.p.kill()
                # else:
                #     kill_child_processes(self.p.pid)
                # # self.p.kill()
        except Exception as e:
            pass
            # print("error in kill_process:", str(e))
        self.p = None

        if reset_device:
            try:
                device_reset(self.adapter_serial)
                # err_msg = gdbrun.gdb_device_reset("", True, self.gdb_port)
                # print("error message output from gdb_device_reset: ", err_msg)
            except Exception as e:
                print("Exception during reset_device:", str(e) )
        
    def write(self, flashaddress, image):
        try:
            
            if not self.tflash:
                self.create_tflash()
            
            if image:
                #below to write action
                print("Start writing: ", image)
                #writebuf = fdesc.read()
                with open(image, "rb") as img_f:
                    writebuf = img_f.read()
            else:
                writebuf = b'\x00' * 2048  # 2KB of null bytes

            amount = self.tflash.pwrite(data=writebuf, offset=flashaddress)
            print(f'{amount} bytes written')
            
            self.tflash.flush()
            #tflash.close()
        
        except Exception as e:
            if "NoneType" in str(e) and "status" in str(e):
                raise swdError("ERROR: write image " + str(image) + ". " + "Device connection lost!!")
            else:
                raise swdError("ERROR: write image " + str(image) + ". " + str(e))
            
    def read(self, flashaddress, length, image):
        try:
            readbuf = self.tflash.pread(offset=flashaddress, count=length)
            
            try:
                if(os.path.isdir(image)):
                    os.makedirs(os.path.dirname(image), exist_ok=True)
                print("Start reading ..")
                with open(image, "wb") as blob_fh:
                    blob_fh.write(readbuf)
                    blob_fh.close()
                print("Read succussful: ", image)
            except Exception as e:
                print("\tERROR: Failed to open " + str(image))
                raise swdError("ERROR: read image " + str(image) + ". " + str(e)) 
            
        except Exception as e:
            if "NoneType" in str(e) and "status" in str(e):
                raise swdError("ERROR: read image " + str(image) + ". " + "Device connection lost!!")
            else:
                raise swdError("ERROR: write image " + str(image) + ". " + str(e))
        
    def read_ptable(self, to_json=""):
        try:
            cur_partition_data = flasher.parts_to_json(self.tflash)
            print(cur_partition_data)
            
            if to_json:
                with open(to_json, "w") as outfile:
                    json.dump(cur_partition_data, outfile, indent=4)
            
            json_string = json.dumps(cur_partition_data, indent=4)
            return json_string

        except Exception as e:
            # print('Exception in read_ptable: ', str(e))
            raise swdError("ERROR: read partition table, " + str(e))
            #return ""
        
    def write_ptable(self, from_json):
        try:
            # flasher.FlashErase.execute(self.tflash,1, 511)
            # time.sleep(0.1)
            
            jsonfile = open(from_json,"r")
            flasher.PartFromJson.execute(self.tflash, jsonfile)
            jsonfile.close()
            time.sleep(0.01)
        
        except Exception as e:
            # print('Exception in write_ptable: ', str(e))
            raise swdError("ERROR: write partition table, " + str(e))
    
    def erase(self, start_sec, end_sector):
        try:
            flasher.FlashErase.execute(self.tflash, start_sec, end_sector)
            time.sleep(0.01)
        
        except Exception as e:
            # print('Exception in Erase partition: ', str(e))
            raise swdError("ERROR: Erase partition, " + str(e))
    
def kill_child_processes(parent_pid, sig=signal.SIGTERM):
    try:
        parent = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)
    for process in children:
        process.send_signal(sig)
    try:
        os.kill(parent_pid, signal.SIGTERM)
    except Exception as e:
        # print("killing the parent pid of openocd Exception: ", str(e))
        pass
        
      # print(process)
      
      
def kill_process(process_name):
       
    # result = os.system(f"taskkill /f /im {process_name}")
    if platform == "win32":
        kill_cmd = f"taskkill /f /im {process_name}"
    else:
        kill_cmd = f"killall -SIGKILL {process_name}"
    try:
        from subprocess import DEVNULL
    except ImportError:
        DEVNULL = os.open(os.devnull, os.O_RDWR)
    
    try:
        result = str(subprocess.check_output(kill_cmd, shell=True, stdin=DEVNULL, stderr=DEVNULL))
    except:
        pass

def fp_follow(file_path):
    with open(file_path, 'r') as f:
        f.seek(0, 1)  # Stay at current position
        while True:
            line = f.readline()
            if not line:
                line = None  # No new line, exit
            yield line

def get_openocd_error(log_stream, check_startup = False):
    no_new_line = False
    return_str = ""
    error_val = False
    while True:
        try:

            line = next(log_stream)
            if line is not None:
                # print("New Line:", line.strip())
                no_new_line = True
                if check_startup:
                    if "cannot read IDR" in line:
                        return 0
                    elif "Listening on port" in line and "for gdb connections" in line:
                        return 1
                elif "target halted due to breakpoint" in line:
                    return_str = "success"
                    error_val = True
                elif "clearing lockup after double fault" in line:
                    return_str = "clearing lockup after double fault"
                    error_val = True
                elif "cannot read IDR" in line:
                    return_str = "cannot read IDR"
                    error_val = True
                elif "Warn : keep_alive() was not invoked" in line:
                    return_str = "Warn : keep_alive() was not invoked"
                    error_val = True
                
                if error_val:
                    while True:
                        line = next(log_stream)
                        if line is None:
                            break

                        if "target halted due to breakpoint" in line:
                            return_str = "success"
                    break
            else:
                break

        except StopIteration:
            time.sleep(0.5)
        except KeyboardInterrupt:
            break
    if check_startup:
        return 2
    else:
        return return_str

import tempfile
def que_for_openocd(mode = "start", que_no = "0\n"):
    try:
        temfile = os.path.join(tempfile.gettempdir(),"tempfile_openocd.txt")
        # temfile = "tempfile_openocd.txt"
        if mode == "start":
            
            # print(temfile)
            if os.path.exists(temfile):
                f = open(temfile, "r+")
                # print(f.readlines())
                lines = f.readlines()
                # print(lines)
                if len(lines)>0:
                    last_line = int(lines[-1]) + 1
                else:
                    last_line = 1
                last_line = str(last_line) + "\n"
                f.write(last_line)
                f.close()
                int_i = 1
                cur_que_no = lines[0]
                while 1:
                    if os.path.exists(temfile):
                        # print("waiting for my task")
                        
                        with open(temfile, "r") as f:
                            new_lines = f.readlines()
                        if new_lines[0] == last_line:
                            # print("starting my task")
                            break
                        
                        time.sleep(0.01)
                        if cur_que_no == new_lines[0]:
                            if int_i == 4:
                                # print("changing the openocd queue to current")
                                with open(temfile, "w") as f:
                                    new_lines = f.write(last_line)
                                int_i = 1
                                cur_que_no = last_line
                            else:
                                int_i = int_i + 1
                            
                        else:
                            int_i = 1
                            cur_que_no = new_lines[0]
                    else:
                        break
                
            else:
                last_line = "1\n"
                f = open(temfile, "w")
                f.write(last_line)
                f.close()
                if 'linux' in os_platform.lower():
                    try:
                        os.chmod(temfile, 0o666)
                        time.sleep(0.1)
                    except Exception as e:
                        # print("Exception on change mode: ", str(e))
                        pass
            return last_line
        else: # end
            if que_no == "0\n":
                return
            if os.path.exists(temfile):
                line_info = []
                with open(temfile, "r") as f:
                    line_info = f.readlines()
                    # print(line_info)
                    
                if len(line_info) == 1 and line_info[0] == que_no:
                    os.remove(temfile)
                    
                else:
                    if que_no in line_info:
                        line_info.remove(que_no)
                    with open(temfile, "w") as f:
                        f.write("".join(line_info))
    except Exception as e:
            
        err_msg = str(e)
        if "permission denied" in err_msg.lower():
            err_msg = "Premission issue, please re-open the tool with sudo privilege."
            raise swdError('Failed to start OpenOCD: ' + err_msg)
        
        if os.path.exists(temfile):
            os.remove(temfile)
            
        return "0\n"

def setup_temp_files():
    #below to sets up initial temporary files to avoid issues with requiring sudo privileges.
    if not os.path.exists("openocd_log"):
        try:
            open("openocd_log", "w").close()
            # change_permission("openocd_log")
            os.chmod("openocd_log", 0o666)
            # time.sleep(0.1)
        except Exception as e:
            # print("Exception on change mode: ", str(e))
            pass

def check_port_number(empty, port_number):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # sock.settimeout(value = 0.01)
        result = sock.connect_ex(('127.0.0.1',port_number))
        if result == 0: #port not available
            sock.close()
            return 1
        else: #port available
            sock.close()
            return 0
        
    except Exception as e:
        raise Exception(str(e))

def build_ftdi_url(serial, interface=None):
        """Forms a ftdi URL."""
        
        vendor = hex(EVK_FTDI_VID)
        product = hex(EVK_FTDI_PID)
        interface = str(interface) if interface else ""     # "base URL" if interface unsupplied
        
        if ";" in serial:
            dev_info = serial.split(";")
            url = "ftdi://" + str(hex(EVK_FTDI_VID)) + ":" + str(hex(EVK_FTDI_PID)) + ":" + str(dev_info[1]) + ":" + str(hex(int(dev_info[2]))) + "/" + interface
        else:
            if serial:
                url = "ftdi://" + vendor + ":" + product + ":" + serial + "/" + interface
            else:
                url = "ftdi://" + vendor + ":" + product + "/" + interface
        
        return url

def prog_flash(serial_no, app_elf, app_elf_addr, status_update, clear_flash, config_file = "", root_img = "", root_img_addr = None, hio_server_port = 10000, no_gdb_reset = False, npu_img = "", npu_addr = None, rfdata_img = "", rfdata_addr = None, boot_arg = "", bootarg_addr = None, reset_device = False):
    # serial_no = "2024-01"
    title_str = ""
    action = "Prog Flash"
    # guiInstQueue = ""
    try:
        if reset_device:
            action = "Reset Device"
            device_reset(serial_no)
            title_str = action + " Completed"
            return

        if clear_flash:
            action = "Clear Flash"

        build_ftdi_url(serial_no)
        # print("device: ", device)

        if not clear_flash and not reset_device:
            if app_elf[-4:] == ".elf":
                app_bin = app_elf[:-4] + ".bin"
                elf_to_bin(app_elf, app_bin)
            else:
                app_bin = app_elf

        # reset device in bl mode
        # reset_evk(device, None)
        
        # serial_no = self.gui_root.devFrame.selBoard.get()
        flasher= swd_flasher_hio_server(adapter_serial = serial_no, hio_server_port = hio_server_port, gang_program = False, clear_flash = clear_flash , no_gdb_reset = no_gdb_reset, reset_device = reset_device) #partition='BOOT', image=r'D:\WIP\14.JIRAS_for_SDK2.7\SWD_prog\checking\sdk_2.7_master\helloworld.img') 
        
        ret_str = flasher.initial_setup()
        if ret_str != "":
            # print("Error occurred in swd_flash_image: " + ret_str)
            raise swdError(ret_str)

        if clear_flash or reset_device:
            # GORDON_SWD = os.path.join(parent_folder, "app", "gordon_erase.elf")
            # print("returning to main")
            title_str = action + " completed"
            return
    
        # flasher.erase(0, 2048)
        # time.sleep(0.02)
        # return 

        # if app_bin:
                    
            # #check image is fit to part
            # ret_str = validate_img_size(app_elf, 'boot')

            # if prog_type == "standard":
                # Generate image file and possibly vm file from elf
            # bootArgs = []

            # if imgFile:
            #     print("writing imgFile: ", imgFile)
            #     flasher.write(0x1000, imgFile)
            #     time.sleep(0.02)

            # if vmFile:
            #     flasher.write(0x40000, vmFile)
            #     time.sleep(0.02)

        if app_bin:
            # print("writing imgFile: ", app_bin)
            flasher.write(app_elf_addr, app_bin)
            time.sleep(0.02)

        if npu_img:
            # print("writing imgFile: ", app_bin)
            flasher.write(npu_addr, npu_img)
            time.sleep(0.02)

        if rfdata_img:
            # print("writing imgFile: ", app_bin)
            flasher.write(rfdata_addr, rfdata_img)
            time.sleep(0.02)

        if boot_arg:
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))

            # Build the full path for the new file
            boot_bin = os.path.join(script_dir, "boot_args.bin")

            # Write data to the file
            with open(boot_bin, "wb") as f:
                f.write(boot_arg.encode('ascii') + b'\x00')

            # print("writing imgFile: ", app_bin)
            flasher.write(bootarg_addr, boot_bin)
            time.sleep(0.02)
            os.remove(boot_bin)
        else:
            flasher.write(bootarg_addr, "") #write null to boot arg address
            time.sleep(0.02)

        title_str = action + " Completed"
        if root_img:
            # #check image is fit to part
            # ret_str = validate_img_size(root_img, 'data')
            # if ret_str != "":
            #     raise swdError(ret_str + " " + os.path.basename(root_img_path) + " not fitting to DATA partition.")
            ret_str = write_fs_image(flasher, serial_no, root_img, root_img_addr, status_update)

            # if "error due to" in ret_str:
            title_str = title_str + " and " + ret_str
        
        # title_str = action + " Completed"
        #reset the device
        # Reset board to boot app from flash
        # reset_evk(device, None, inhibitFlashBoot=False)
        print(title_str)

    except Exception as e:
        # print(action + " except", str(e))
        try:
            if flasher.hio_serv.err_msg:
                title_str = action + " error due to:" + flasher.hio_serv.err_msg
            elif flasher.tflasher_err:
                title_str = action + " error due to: " + flasher.tflasher_err
            else:
                title_str = action + " error due to: " + str(e)
        except:
            title_str = action + " error due to: " + str(e)

        raise Exception(title_str)
    finally:

        try:
            if app_elf != app_bin:
                os.remove(app_bin)
        except:
            pass

        try:
            flasher.close_setup()
            
        except Exception as e:
            pass

        if "error due to" not in title_str:
            if status_update:
                status_update.emit({"done": title_str})

        try:
            os.remove(os.path.join(tempfile.gettempdir(),"tempfile_openocd.txt"))
        except:
            pass

        if clear_flash or reset_device:
            print(title_str)

def write_fs_image(flasher, serial_no, img_file, fs_addr, status_update, hio_server_port = 10000):
    # serial_no = "2024-01"
    title_str = ""
    action = "Write FS image"
    # guiInstQueue = ""
    flasher_close = True
    try:

        build_ftdi_url(serial_no)
        # print("device: ", device)

        # reset device in bl mode
        # reset_evk(device, None)
        
        if flasher is None:
            # serial_no = self.gui_root.devFrame.selBoard.get()
            flasher= swd_flasher_hio_server(adapter_serial = serial_no, hio_server_port = hio_server_port, gang_program = False ) #partition='BOOT', image=r'D:\WIP\14.JIRAS_for_SDK2.7\SWD_prog\checking\sdk_2.7_master\helloworld.img') 
        
            ret_str = flasher.initial_setup()
            if ret_str != "":
                # print("Error occurred in swd_flash_image: " + ret_str)
                raise swdError(ret_str)
        else:
            flasher_close = False
        
    
        flasher.write(fs_addr, img_file)
        time.sleep(0.02)

        title_str = action + " Completed"
        #reset the device
        # Reset board to boot app from flash
        # reset_evk(device, None, inhibitFlashBoot=False)      
        print(title_str)
        return title_str
    
    except Exception as e:
        # print(action + " except", str(e))
        try:
            if flasher.hio_serv.err_msg:
                title_str = action + " error due to:" + flasher.hio_serv.err_msg
            elif flasher.tflasher_err:
                title_str = action + " error due to: " + flasher.tflasher_err
            else:
                title_str = action + " error due to: " + str(e)
        except:
            title_str = action + " error due to: " + str(e)

        raise Exception(title_str)
    
    finally:

        try:
            os.remove(os.path.join(tempfile.gettempdir(),"tempfile_openocd.txt"))
        except:
            pass

        if flasher_close:
            try:
                flasher.close_setup()
                
            except Exception as e:
                pass    

        if "error due to" not in title_str:
            if status_update:
                status_update.emit({"done": title_str})    

def read_fs_image(flasher, serial_no, img_file, read_addr, read_size, status_update, hio_server_port = 10000):
    # serial_no = "2024-01"
    title_str = ""
    action = "Read FS image"
    # guiInstQueue = ""
    flasher_close = True
    try:

        build_ftdi_url(serial_no)
        # print("device: ", device)

        # reset device in bl mode
        # reset_evk(device, None)
        
        if flasher is None:
            # serial_no = self.gui_root.devFrame.selBoard.get()
            flasher= swd_flasher_hio_server(adapter_serial = serial_no, hio_server_port = hio_server_port ) #partition='BOOT', image=r'D:\WIP\14.JIRAS_for_SDK2.7\SWD_prog\checking\sdk_2.7_master\helloworld.img') 
        
            ret_str = flasher.initial_setup()
            if ret_str != "":
                # print("Error occurred in swd_flash_image: " + ret_str)
                raise swdError(ret_str)
        else:
            flasher_close = False
        
    
        flasher.read(read_addr, read_size, img_file)
        time.sleep(0.02)

        title_str = action + " Completed"
        #reset the device
        # Reset board to boot app from flash
        # reset_evk(device, None, inhibitFlashBoot=False)      
        print(title_str)
        return title_str
    
    except Exception as e:
        # print(action + " except", str(e))
        try:
            if flasher.hio_serv.err_msg:
                title_str = action + " error due to:" + flasher.hio_serv.err_msg
            elif flasher.tflasher_err:
                title_str = action + " error due to: " + flasher.tflasher_err
            else:
                title_str = action + " error due to: " + str(e)
        except:
            title_str = action + " error due to: " + str(e)

        raise Exception(title_str)
    
    finally:

        try:
            os.remove(os.path.join(tempfile.gettempdir(),"tempfile_openocd.txt"))
        except:
            pass

        if flasher_close:
            try:
                flasher.close_setup()
                
            except Exception as e:
                pass

        if "error due to" not in title_str:
            if status_update:
                status_update.emit({"done": title_str})

def replace_line_in_file(file_path, match_string, new_line):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    with open(file_path, 'w') as file:
        for line in lines:
            if match_string in line and "exec python" in line:
                # print("found the line and replaced")
                file.write(new_line + '\n')
            else:
                file.write(line)
                
def device_reset(serial_no, internal=False):
    if platform == 'win32' and not internal:
        # Launch a separate process to perform the reset to avoid USB interface contention
        # on Windows with libusb0-dll.
        try:
            cmd = [sys.executable, __file__, "--internal_reset", "--serial", serial_no]
            if getattr(sys, 'frozen', False):
                # If running as a frozen executable, the __file__ might not be boot.py
                # but the executable itself handles the flag in __main__.py
                cmd = [sys.executable, "--internal_reset", "--serial", serial_no]
            
            print(f"Launching reset subprocess: {' '.join(cmd)}")
            subprocess.check_call(cmd)
            return
        except Exception as e:
            print(f"Failed to launch reset subprocess: {e}. Falling back to inline reset.")

    import reset
    reset.reset("evk42", ftdi_serial=serial_no)

from convert_elf_2_bin import *
import bits.bootargs
if __name__ == "__main__":
    # python3 boot.py --serial 30005015 --app_elf ../elfs/hello_world_11.elf --app_addr 0x0

    try:
        current_directory = os.getcwd()

        current_folder = os.path.dirname(os.path.abspath(__file__))
        print("current_folder: ", current_folder)
        # # Get the parent directory (one step up)
        parent_folder = os.path.dirname(current_folder)

        GORDON_ERASE = os.path.join(current_folder, "resources", "gordon_erase.elf")
        GORDON_SWD = os.path.join(current_folder, "resources", "gordon_swd.elf")

        SDK_FILES = os.path.join(current_folder, "resources", "conf") #"../conf"

        #below manual test for read
        # read_fs_image(None, "30005015", "./data.img", int('0x5FF000', 16), int('0x200000', 16), None)
        # sys.exit()

        #below manual test for write
        # write_fs_image(None, "30005015", "/home/uselvakalathi/ulaga/T3_WIP/img_test/data_image2.img", int('0x5FF000', 16), None)
        # sys.exit()

        import argparse

        parser = argparse.ArgumentParser(description="""Example commands:
                                        
    Clear Flash: python3 boot.py --clear_flash
        Note: incase of multiple device connect, use --serial argument to select the particular device
		e.g: Clear Flash: python3 boot.py --serial 30005015 --clear_flash

    Reset Device: python3 boot.py --reset_device

    Program Flash: python3 boot.py --app_elf ../apps/hello_world/bin/hello_world.elf --npu_img ../apps/npu/npu.bin --boot_arg "hio.baudrate=921600 hio.maxsize=1600"
                                         
        Note:
            1. --serial, --app_addr, --npu_addr, and --bootarg_addr can be provided to override the default flash addresses.
            2. All arguments are optional; provide only those that are required.

    Write filesystem image to flash:
        python3 boot.py --fs_img ../apps/data.img --fs_addr 0x00580000

    Read filesystem image from flash:
        python3 boot.py --out_img ./data.img --read_addr 0x00580000 --read_size 0x00280000
                                                                    
                                        """,
            formatter_class=argparse.RawDescriptionHelpFormatter)

        # Define named arguments
        parser.add_argument(
            '--serial',
            type=str,
            default="",
            help='Device serial number (e.g., 30005015). '
                'If not provided, the device is identified automatically. '
                'When multiple devices are connected, one is selected at random.'
        )
        parser.add_argument('--app_elf', type=str, default="", help='Application ELF image file')
        parser.add_argument('--app_addr', type=str, default=0x00, help='Application image flash address. Default: 0x00')

        parser.add_argument('--dev_conf', type=str, default="", help='Configuration JSON file')

        parser.add_argument('--fs_img', type=str, default="", help='Filesystem image (.img) file to write')
        parser.add_argument('--fs_addr', type=str, default=0x00580000,
                            help='Filesystem image start address. Default: 0x00580000')

        parser.add_argument('--out_img', type=str, default="", help='Output image (.img) file for read operation')
        parser.add_argument('--read_addr', type=str, default="", help='Flash start address to read (e.g., 0x00580000)')
        parser.add_argument('--read_size', type=str, default="", help='Size to read (e.g., 0x00280000)')

        parser.add_argument('--clear_flash', action='store_true', help='Erase the entire flash')
        parser.add_argument('--run_app', action='store_true',
                            help='Load and run the application ELF via GDB/RAM instead of flashing')
        parser.add_argument('--no_gdb_reset', action='store_true',
                            help='Skip GDB reset via SWD during Clear Flash and Program Flash operations')

        parser.add_argument('--npu_img', type=str, default="", help='NPU application image (.bin) file to write')
        parser.add_argument('--npu_addr', type=str, default=0x00280000,
                            help='NPU application image start address. Default: 0x00280000')

        parser.add_argument('--boot_arg', type=str, default="",
                            help='Boot argument string (space-separated), e.g., "hio.baudrate=921600 hio.maxsize=1600"')

        parser.add_argument('--bootarg_addr', type=str, default=0x00200000,
                            help='Boot argument start address. Default: 0x00200000')
        parser.add_argument('--reset_device', action='store_true', 
                            help='Flag to perform device reset')
        parser.add_argument('--internal_reset', action='store_true', 
                            help=argparse.SUPPRESS) # Internal use for Windows subprocess reset

        # Check if no arguments are passed
        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit(1)

        args = parser.parse_args()

        if not args.serial:
            usb_tuple_list = UsbTools.find_all([(EVK_FTDI_VID, EVK_FTDI_PID)], nocache=True)
            if len(usb_tuple_list) <= 0:
                print("Can't find any ftdi device")
                sys.exit()
            args.serial = usb_tuple_list[0][0].sn

        serial_no = args.serial
        if args.reset_device:
            print("Device reset")
            prog_flash(serial_no, "", 0, None, args.clear_flash, reset_device = True)
            sys.exit()

        if args.internal_reset:
            device_reset(serial_no, internal=True)
            sys.exit()

        if args.clear_flash:
            print("Clear flash")
            prog_flash(serial_no, "", 0, None, args.clear_flash, no_gdb_reset = args.no_gdb_reset)
            sys.exit()
        else:
            print("prog flash")

        app_elf_addr = None
        try:
            app_elf_addr = int(args.app_addr, 16)
        except:
            try:
                app_elf_addr = int(args.app_addr)
            except:
                pass

        npu_app_addr = None
        try:
            npu_app_addr = int(args.npu_addr, 16)
        except:
            try:
                npu_app_addr = int(args.npu_addr)
            except:
                pass
        
        bootarg_addr = None
        try:
            bootarg_addr = int(args.bootarg_addr, 16)
        except:
            try:
                bootarg_addr = int(args.bootarg_addr)
            except:
                pass

        fs_addr = None
        try:
            fs_addr = int(args.fs_addr, 16)
        except:
            try:
                fs_addr = int(args.fs_addr)
            except:
                pass

        read_addr = None
        try:
            read_addr = int(args.read_addr, 16)
        except:
            try:
                read_addr = int(args.read_addr)
            except:
                pass

        read_size = None
        try:
            read_size = int(args.read_size, 16)
        except:
            try:
                read_size = int(args.read_size)
            except:
                pass

        if args.out_img: #read flash mem to image file
            miss_str = ""
            if read_addr is None and read_size is None:
                miss_str = "--read_addr and --read_size arguments not provided"
            elif read_addr is None:
                miss_str = "--read_addr argument not provided"
            elif read_size is None:
                miss_str = "--read_size argument not provided"
            
            if miss_str:
                raise Exception(miss_str)

            read_fs_image(None, serial_no, args.out_img, read_addr, read_size, None)
            sys.exit()

        if args.fs_img and not args.app_elf: #only write fs image
            if os.path.isfile(os.path.join(current_directory, args.fs_img)):
                if fs_addr is None:
                    raise Exception("--fs_addr argument not provided")

                write_fs_image(None, serial_no, args.fs_img, fs_addr, None)
                sys.exit()
            else:
                raise Exception("Input fs_img file doesn't exist: " + str(args.fs_img))

        if args.fs_img:
            if not os.path.isfile(os.path.join(current_directory, args.fs_img)):
                raise Exception("Input fs_img file doesn't exist: " + str(args.fs_img))

            else:
                if fs_addr is None:
                    raise Exception("--fs_addr argument not provided")

        if args.app_elf:
            if not os.path.isfile(os.path.join(current_directory, args.app_elf)):
                raise Exception("Input app_elf file doesn't exist: " + str(args.app_elf))

            if args.dev_conf:
                if not os.path.isfile(os.path.join(current_directory, args.dev_conf)):
                    raise Exception("Input dev_conf file doesn't exist: " + str(args.dev_conf))

        if args.npu_img:
            if not os.path.isfile(os.path.join(current_directory, args.npu_img)):
                raise Exception("Input app_elf file doesn't exist: " + str(args.npu_img))

        if args.run_app:
            if not args.app_elf:
                print("--run_app requires --app_elf")
                sys.exit(1)

            serial_no = args.serial

            flasher = swd_flasher_hio_server(
                adapter_serial=serial_no,
                hio_server_port=10000,
                gang_program=False,
                clear_flash=False
            )
            flasher.run_app = True

            if not args.dev_conf:
                flasher.app_elf = args.app_elf   # reuse the same ELF
            elif args.dev_conf:
                flasher.app_elf = update_dev_conf.main(args.dev_conf, args.app_elf)

            ret_str = flasher.initial_setup()
            # start_hio_server() will take the run-app branch
            sys.exit(0)


        # print(parser)
        inp_elf = args.app_elf
        # img_bin = inp_elf[:-4] + ".bin"
        # elf_to_bin(inp_elf, img_bin)

        # app_elf_addr = 0x00
        # print(app_elf_addr, type(app_elf_addr))

        print(inp_elf, app_elf_addr, serial_no)
        prog_flash(serial_no, inp_elf, app_elf_addr, None, False, config_file = args.dev_conf, root_img = args.fs_img, root_img_addr = fs_addr, no_gdb_reset = args.no_gdb_reset, npu_img = args.npu_img, npu_addr = npu_app_addr, boot_arg = args.boot_arg, bootarg_addr = bootarg_addr) #REMOVE FOR IFX BUILD

    except Exception as e:
        print(str(e))
        sys.exit(1)
