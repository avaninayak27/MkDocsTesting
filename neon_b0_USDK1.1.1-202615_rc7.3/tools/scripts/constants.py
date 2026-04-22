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

# Program version
VERSION = "x.y"

#Trademark Symbol
TM = u'\u2122'

# VID and PID of FTDI chip on EVK
EVK_FTDI_VID = 0x403
EVK_FTDI_PID = 0x6011


# FTDI interfaces
EVK_FTDI_JTAG_INTERFACE = 1
EVK_FTDI_RESET_INTERFACE = 2
EVK_FTDI_SPI_INTERFACE = 2
EVK_FTDI_UART_PROG_INTERFACE = 3
EVK_FTDI_CONSOLE_INTERFACE = 4

EVK_FTDI_RESET_PIN = 7        # Reset pin on reset interface

EVK_FTDI_CONSOLE_BAUDRATE = 921600 #2457600
