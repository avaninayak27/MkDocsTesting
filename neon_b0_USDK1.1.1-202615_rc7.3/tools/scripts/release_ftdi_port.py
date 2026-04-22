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

import os, sys
import serial, time
from serial import SerialException
import pyftdi.serialext     # Needed to register pyftdi as a pyserial backend

def attach_device(device_url):
    if device_url:
        print("input device_url", device_url)
        if not ("ftdi://" in device_url):
            print("input device_url is not in required format")
            return
        else:
            device_url_inter = device_url.split("/")[-1]
            device_url = device_url[:len(device_url)-len(device_url_inter)]

    else:
        print("No input")

    print("modified device_url: ", device_url)
    for i in range(1, 5):
        # url = "ftdi://0x403:0x6011:2023-0/" + str(i)
        url = device_url + str(i)
        print(url)
        args = {}
        kwargs = {'baudrate': 2457600, 'timeout': 0.1}
        port = None
        try:
            print("current wdir: ", os. getcwd())
            port = serial.serial_for_url(url, *args, **kwargs)
            time.sleep(1)
        except (SerialException, Exception) as e:
            print("Exception : ", str(e))

        finally:
            if port:
                # Might be in a bad state; ignore exceptions when trying to close
                try:
                    port.close()
                except (SerialException, Exception) as e:
                    print("Exception : ", str(e))
            else:
                print("No port")

if __name__ == "__main__":
    #below for manual test
    # attach_device("ftdi://0x403:0x6011:30005015/4")
    # sys.exit()

    if len(sys.argv) < 0:
        print("Device ftdi url is need as input arg, example ftdi://0x403:0x6011:2023-0/, where device number is 2023-0")
        sys.exit(1)
    os.system("pip3 install pyftdi")
    # Passing command line arguments to the class constructor
    attach_device(sys.argv[1])
    # script = MyScript(sys.argv[1], sys.argv[2])
    # script.display()

    
