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

"""WiFi Manager Interface.

This is an interface to the WIFI Connection Manager. This interface containts operations for:

<ul>
  <li> Create and destroy Wi-Fi interface </li>
  <li> Set and get Ipv4 address </li>
  <li> Set and get Ipv6 address </li>
  <li> Add/Remove network profile </li>
  <li> Connect/Disconnect to a network </li>
  <li> Set/Get Tx Power in dBm/vBm </li>
  <li> Set/Get Mac address </li>
  <li> Set/Get Power Save configuration </li>
  <li> Enable/Disable PMF configuration </li>
  <li> Set/Get the current regulatory domain info </li>
  <li> Set/Get the country code </li>
  <li> Set /Get MFG command </li>
  <li> Registers/ Unregisters interest in a multicast address </li>
  <li> Setup/teardown/join TWT session and send TWT information </li>
  <li> Configure Wi-Fi HE OMI parameters </li>
  <li> Get current network information (SSID/BSSID/Channel/Auth mode/RSSI/Wi-Fi Statistics etc.) </li>
  <li> Get FW(chip) Capability and WLAN firmware version </li>
  <li> Notifying status change in Wi-Fi connection </li>
  <li> Notify Scan results and status </li>
</ul>
"""
import os
import json
from pathlib import Path

from hio.base import message, status
from hio.base import uint8, uint16, uint32, uint64
from hio.base import int8, int16, int32
from hio.base import string
from hio.base import macaddr
from hio.base import ipaddr4, ipaddr6

# Automatically set GROUP_NAME and GROUP_ID based on file name and hio_config.json
_FILE_NAME = Path(__file__).stem
_CONFIG_PATH = Path(__file__).parent.parent / 'hio_config.json'

with open(_CONFIG_PATH) as f:
    _CONFIG = json.load(f)

GROUP_NAME = _FILE_NAME
GROUP_ID = _CONFIG[_FILE_NAME]['group_id']

class initialize(message):
    '''Initialize and create a WiFi network interface.'''
    req   = [
       uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
    ]

class deinit(message):
    '''Deinitialize and destroy a WiFi network interface.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
    ]

class status_notify(message):
    '''Notifying status change in wifi connection.'''
    ind   = [
        uint32("status", doc='Notification type: Connected (0), Disconnected (1), IPv4 Configuration done (2), IPv6 Configuration done (3), IPv4 Address change (4), IPv6 Address change (5)'),
        uint32("error_code", doc='Error code incase of failure: AP not found (1), Assoc Response error (2), AP deauthenticated during connection procedure (3), Wrong passphrase (4), DHCP timeout (5)')
    ]

class add_network_profile(message):
    '''Add network profile to connect to.'''
    req   = [
        string("ssid", array=33, doc='SSID of the network'),
        string("passphrase", array=64, doc='Passphrase of the network'),
        string("sae_password", array=64, doc='SAE Password of the network'),
        string("sae_password_id", array=256, doc='SAE Password ID of the network'),
        string("eap_passphrase", array=128, doc='EAP Passphrase of the network'),
        string("eap_identity", array=256, doc='EAP Passphrase Identity of the network'),
        uint32("assoc_listen_interval", doc='Association Listen Interval'),
        uint8("bssid", array=6, doc='BSSID of the network'),
    ]
    rsp   = [
        status(),
    ]

class remove_network_profile(message):
    '''Remove current network profile.'''
    req   = [
        uint8("ssid_len", doc='Length of the SSID excluding the zero terminating byte'),
        string("ssid", array=33, doc='SSID of the network'),
        uint8("bssid", array=6, doc='BSSID of the network'),
    ]
    rsp   = [
        status(),
    ]

class connect(message):
    '''Connect to a network configured by add network request.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
    ]

class disconnect(message):
    '''Disconnect from current network.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
    ]

class set_network_ipv4_address(message):
    '''Set interface IPv4 address.'''
    req   = [
        ipaddr4("ipaddr4",    doc='Address, as big-endian integer'),
        ipaddr4("netmask",    doc='Netmask, as big-endian integer'),
        ipaddr4("gw",         doc='Default-route, as big-endian integer'),
        ipaddr4("dns_server", doc='DNS server, as big-endian integer'),
    ]
    rsp   = [
        status(),
    ]

class get_network_ipv4_address(message):
    '''Get current IPv4 address.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        ipaddr4("ipaddr4",    doc='Address, as big-endian integer'),
        ipaddr4("netmask",    doc='Netmask, as big-endian integer'),
        ipaddr4("gw",         doc='Default-route, as big-endian integer'),
        ipaddr4("dns_server", doc='DNS server, as big-endian integer'),
    ]

class set_network_ipv6_address(message):
    '''Set interface IPv6 address.'''
    req   = [
        uint32('addr6_idx', doc='Address index and MUST be >= 0. NOTE that index 0 is link-local IPv6 address'),
        ipaddr6("ipaddr6",  doc='Interface IPv6 address'),

    ]
    rsp   = [
        status(),
    ]

class get_network_ipv6_address(message):
    '''Get current IPv6 address.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        uint32('numaddress', doc=' number of address'),
        ipaddr6("ipaddr6", array=64, doc='interface list of IPv6 addresses'),
    ]

class scan(message):
    '''Scan for WiFi networks.'''
    req   = [
        uint8("num_probes", doc='Max number of probes to send in active scan'),
        uint8("idle_slots", doc='Max number of idle slots to decide if we should keep listening'),
        uint8("channel_mask", array=8, doc='List of channels to scan'),
        uint8("bssid", array=6, doc='Destination address and BSSID for probe requests'),
        uint16("txrate", doc='Rate to use for sending probe requests'),
        uint8("has_ssid", doc='Scan request included SSID or not'),
        uint8("ssid_len", doc='Length of the SSID excluding the zero terminating byte'),
        string("ssid", array=33, doc='SSID with zero termination. An SSID should be treated as binary data but adding zero termination simplifies code using this parameter'),
        uint32("min_listen_time", doc='The min time (in milliseconds) to listen for probe responses on the channel after sending a probe'),
        uint32("max_listen_time", doc='The max time (in milliseconds) including listen and probe request to stay on a channel'),
        uint32("probe_tx_timeout", doc='The timeout (in milliseconds) a probe request is aborted if transmission was not possible'),
        uint32("wait_time", doc='Idle time between each channel (giving other parties access to the media'),
        uint32("max_responses", doc='Max number of scan probe response results'),
    ]
    rsp   = [
        status(),
    ]
    ind   = [
        int32("scan_status", doc='Scan status: Scan is not finished (0), Successful completion of scan (1), Scan is aborted due to error (2)'),
        uint16("beacon_int", doc='Beacon interval in TU'),
        uint16("capab", doc='Capabilities field'),
        uint64("timestamp", doc='Timestamp'),
        int16("rssi", doc='RSSI'),
        uint16('fc', doc='Frame control'),
        uint8("bssid", array=6, doc='The networks BSSID'),
        uint8("channel", doc='Active channel number, zero if unknown'),
        uint8("has_ssid", doc='Scan request included SSID or not'),
        uint8("ssid_len", doc='Length of the SSID excluding the zero terminating byte'),
        string("ssid", array=33, doc='IE SSID (if exists)'),
        uint32("ielist_count", doc='Number of information elements'),
        uint32("ie_list_len", doc='Length of information elements'),
        uint8("ielist", array=0, doc='List of information elements (variable length)'),
    ]

class scan_stop(message):
    '''Stop the scan in process.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
    ]

class get_channel(message):
    '''Get current channel.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        uint32("channel", doc='The IEEE802.11 channel number'),
    ]

class get_bssid(message):
    '''Get the BSSID.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        uint8("bssid", array=6, doc='MAC address'),
    ]

class get_authmode(message):
    '''Get authentication mode.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        uint32("auth_mode", doc='Current authentication mode: WPA personal - BIT(0), WPA2 personal - BIT(1), WPA3 personal - BIT(2), WPA enterprise - BIT(3), WPA2/WPA3 enterprise - BIT(4), Management frame protection capable - BIT(6), Management frame protection required - BIT(7)'),
        uint8("mpf_status", doc='Current MPF status: MFP not required (0), MFP Capable (1), MFP required (2)'),
    ]

class get_rssi(message):
    '''Get the RSSI.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        int32("rssi", doc='RSSI Info'),
    ]

class omi_config(message):
    '''Configure WIFi HE OMI parameters.'''
    req   = [
        uint8("ul_ofdma_disable", doc='Uplink OFDMA Disable'),
        uint8("ul_ofdma_data_disable", doc='Uplink OFDMA Data Disable'),
    ]
    rsp   = [
        status(),
    ]

class set_powersave(message):
    '''Set/Update WiFi Power Save configuration.'''
    req   = [
        uint8("enabled", doc='Power Save enabled'),
        uint32("listen_interval", doc='Listen interval in units of beacon intervals'),
        uint32("traffic_tmo", doc='Traffic timeout (in ms)'),
        uint8("ps_poll", doc='Set 1 to use ps poll when beacon was missed'),
        uint8("dyn_listen_int", doc='Set 1 to listen to all beacons if there was traffic recently'),
        uint8("sta_rx_nap", doc='Turn off receiver for uninteresting frames for station'),
        uint8("sta_only_broadcast", doc='Do not receive multicast frames that are not broadcast (only effective if rx_nap is used)'),
        uint8("tx_ps", doc='Send outgoing frames without leaving WiFi power save'),
        uint8("mcast_dont_care", doc='Ignore the multicast flag in beacons. Use this function with care. Incoming broadcast ARPs or other important broadcast/multicast traffic may be missed'),
        uint16("extend_wakeup_ms", doc='Once woken up, extend in that state by this time in ms to check next packets. This is used for increased throughput in PS mode'),
        uint8("ulp_mode", doc='Mode to be set for ULP(DS0/DS1/DS2) 1 for DS1, 2 for DS2 and 0 indicates to disable(DS0)'),
        uint16("ulp_wait", doc='If no network activity for this time, device will enter into DS2'),
    ]
    rsp   = [
        status(),
    ]

class get_powersave(message):
    '''Get Current WiFi Power Save Configuration.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        uint8("enabled", doc='Power Save enabled'),
        uint32("listen_interval", doc='Listen interval in units of beacon intervals'),
        uint32("traffic_tmo", doc='Traffic timeout (in ms)'),
        uint8("ps_poll", doc='Set 1 to use ps poll when beacon was missed'),
        uint8("dyn_listen_int", doc='Set 1 to listen to all beacons if there was traffic recently'),
        uint8("sta_rx_nap", doc='Turn off receiver for uninteresting frames for station'),
        uint8("sta_only_broadcast", doc='Do not receive multicast frames that are not broadcast (only effective if rx_nap is used)'),
        uint8("tx_ps", doc='Send outgoing frames without leaving WiFi power save'),
        uint8("mcast_dont_care", doc='Ignore the multicast flag in beacons. Use this function with care. Incoming broadcast ARPs or other important broadcast/multicast traffic may be missed'),
        uint16("extend_wakeup_ms", doc='Once woken up, extend in that state by this time in ms to check next packets. This is used for increased throughput in PS mode'),
        uint8("ulp_mode", doc='Mode to be set for ULP(DS0/DS1/DS2) 1 for DS1, 2 for DS2 and 0 indicates to disable(DS0)'),
        uint16("ulp_wait", doc='If no network activity for this time, device will enter into DS2'),
    ]

class set_mac(message):
    '''Set MAC address for WiFi interface.'''
    req   = [
        uint8("mac_addr", array=6, doc='MAC address'),
    ]
    rsp   = [
        status(),
    ]

class get_mac(message):
    '''Get MAC address of WiFi interface.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        uint8("mac_addr", array=6, doc='MAC address'),
    ]

class set_max_tx_power(message):
    '''Set the WiFi TX power in dBm.'''
    req   = [
        int8("power", doc='Max TX power in dBm'),
    ]
    rsp   = [
        status(),
    ]

class get_max_tx_power(message):
    '''Get current maximum Wi-Fi Tx power in dBm'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        int8("power", doc='Max TX power in dBm'),
    ]

class set_max_tx_power_vbm(message):
    '''Set the WiFi TX power in vBm.'''
    req   = [
        int8("power_vbm", doc='Max TX power in vBm'),
    ]
    rsp   = [
        status(),
    ]

class get_max_tx_power_vbm(message):
    '''Get current maximum Wi-Fi Tx power in vBm.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        int8("power_vbm", doc='Max TX power in vBm'),
    ]

class itwt_setup(message):
    '''Setup Individual Target Wake Time (ITWT).'''
    req   = [
        uint8("setup_cmd", doc='TWT Command'),
        uint8("flow_flags", doc='Flow attributes'),
        uint8("flow_id", doc='Flow indentifiacation, must be between 0 and 7. Set 0xFF for auto assignment'),
        uint8("wake_type", doc='TWT wake type'),
        uint32("wake_time_h", doc='Target Wake Time - BSS TSF (us)'),
        uint32("wake_time_l", doc='Target Wake Time - BSS TSF (us)'),
        uint32("wake_dur", doc='Target wake duration in unit of microseconds'),
        uint32("wake_int", doc='Target wake interval'),
        uint32("btwt_persistence", doc='Broadcast TWT Persistence'),
        uint32("wake_int_max", doc='Max wake interval(uS) for TWT'),
        uint8("duty_cycle_min", doc='Min duty cycle for TWT(Percentage)'),
        uint8("pad", doc='Max TX power in vBm'),
        uint8("bid", doc='Must be between 0 and 31. Set 0xFF for auto assignment'),
        uint8("channel", doc='Twt channel'),
        uint8("negotiation_type", doc='Negotiation Type'),
    ]
    rsp   = [
        status(),
    ]

class itwt_teardown(message):
    '''Teardown Individual Target Wake Time (ITWT).'''
    req   = [
        uint8("negotiation_type", doc='Negotiation Type'),
        uint8("flow_id", doc='Flow indentifiacation, must be between 0 and 7. Set 0xFF for auto assignment'),
        uint8("bid", doc='Must be between 0 and 31. Set 0xFF for auto assignment'),
        uint8("alltwt", doc='Set 1 to tear down all twt session'),
    ]
    rsp   = [
        status(),
    ]

class twt_join(message):
    '''Join broadcast TWT session(used by STA).'''
    req   = [
        uint8("setup_cmd", doc='TWT Command'),
        uint8("flow_flags", doc='Flow attributes'),
        uint8("flow_id", doc='Flow indentifiacation, must be between 0 and 7. Set 0xFF for auto assignment'),
        uint8("wake_type", doc='TWT wake type'),
        uint32("wake_time_h", doc='Target Wake Time - BSS TSF (us)'),
        uint32("wake_time_l", doc='Target Wake Time - BSS TSF (us)'),
        uint32("wake_dur", doc='Target wake duration in unit of microseconds'),
        uint32("wake_int", doc='Target wake interval'),
        uint32("btwt_persistence", doc='Broadcast TWT Persistence'),
        uint32("wake_int_max", doc='Max wake interval(uS) for TWT'),
        uint8("duty_cycle_min", doc='Min duty cycle for TWT(Percentage)'),
        uint8("pad", doc='Max TX power in vBm'),
        uint8("bid", doc='Must be between 0 and 31. Set 0xFF for auto assignment'),
        uint8("channel", doc='Twt channel'),
        uint8("negotiation_type", doc='Negotiation Type'),
    ]
    rsp   = [
        status(),
    ]

class twt_information_frame_send(message):
    '''Send a Target Wake Time (TWT) information frame.'''
    req   = [
        uint8("flow_flags", doc='Flow attributes'),
        uint8("flow_id", doc='Flow indentifiacation, must be between 0 and 7. Set 0xFF for auto assignment'),
        uint32("next_twt_h", doc='Next scheduled TWT'),
        uint32("next_twt_l", doc='Next scheduled TWT'),
    ]
    rsp   = [
        status(),
    ]

class set_regulatory_domain(message):
    '''Set the current regulatory domain info.'''
    req   = [
        string("domain", array=64, doc='FCC, ETSI, TELEC, KCC, SRCC (or e.g. 1..11@20)'),
    ]
    rsp   = [
        status(),
    ]

class get_regulatory_domain(message):
    '''Get the current regulatory domain info.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        string("domain", array=64, doc='FCC, ETSI, TELEC, KCC, SRCC (or e.g. 1..11@20)'),
    ]

class disable_pmf(message):
    '''Disable PMF configuration.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
    ]

class enable_pmf(message):
    '''Enable PMF configuration.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
    ]

class set_country_code(message):
    '''Set the country code.'''
    req   = [
        string("country_code", array=3, doc='Null terminated country code'),
        uint8("ieee80211d_enabled", doc='IEEE80211d mode enabled'),
    ]
    rsp   = [
        status(),
    ]

class get_country_code(message):
    '''Get the current country code.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        string("country_code", array=3, doc='Null terminated country code'),
    ]

class get_ap_info(message):
    '''Get information of AP to which the device is connected to.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        uint16("beacon_int", doc='Beacon interval in TU'),
        uint16("capab", doc='Capabilities field'),
        uint64("timestamp", doc='Timestamp'),
        int16("rssi", doc='RSSI'),
        uint16('fc', doc='Frame control'),
        uint8("bssid", array=6, doc='The networks BSSID'),
        uint8("channel", doc='Active channel number, zero if unknown'),
        uint8("has_ssid", doc='Scan request included SSID or not'),
        uint8("ssid_len", doc='Length of the SSID excluding the zero terminating byte'),
        string("ssid", array=33, doc='IE SSID (if exists)'),
        uint32("ielist_count", doc='Number of information elements'),
        uint32("ie_list_len", doc='Length of information elements'),
        uint8("ielist", array=0, doc='List of information elements (variable length)'),
    ]

class get_stats(message):
    '''Dump WiFi statistics.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        uint32("tx", array=32, doc='tx'),
        uint32("tx_ack", array=32, doc='tx_ack'),
        uint32("txa_mcs", array=8, doc='txa_mcs'),
        uint32("txa_nof", doc='txa_nof'),
        uint32("txa_subframes", doc='txa_subframes'),
        uint32("txa_ba", doc='txa_ba'),
        uint32("txa_ba_num", doc='txa_ba_num'),
        uint32("txa_ba_hits", doc='txa_ba_hits'),
        uint32("tx_timeout", doc='tx_timeout'),
        uint32("rx", array=32, doc='rx'),
        uint32("rxa_mcs", array=8, doc='rxa_mcs'),
        uint32("rxa_accept", array=8, doc='rxa_accept'),
        uint32("rxa_fail", array=8, doc='rxa_fail'),
        uint32("rx_no_pkt", doc='rx_no_pkt'),
        uint32("rx_no_frag", doc='rx_no_frag'),
        uint32("rts_tx", doc='rts_tx'),
        uint32("cts_rx", doc='cts_rx'),
    ]

class mcast_addr_add(message):
    '''Registers interest in a multicast address.'''
    req   = [
        uint8("mac_addr", array=6, doc='MAC address'),
    ]
    rsp   = [
        status(),
    ]

class mcast_addr_del(message):
    '''Unregisters interest in a multicast address.'''
    req   = [
        uint8("mac_addr", array=6, doc='MAC address'),
    ]
    rsp   = [
        status(),
    ]

class set_static_rate(message):
    '''Set static rate.'''
    req   = [
        uint32("rate_format", doc='Rate Format'),
        uint32("rate_index", doc='Rate Index'),
        uint32("gi", doc='Gaurd Interval'),
    ]
    rsp   = [
        status(),
    ]

class get_static_rate(message):
    '''Get static rate.'''
    req   = [
        uint32("handle", doc='Interface handle (Optional argument)'),
    ]
    rsp   = [
        status(),
        uint32("rate_format", doc='Rate Format'),
        uint32("rate_index", doc='Rate Index'),
        uint32("gi", doc='Gaurd Interval'),
    ]

class get_wifi_link_status(message):
    '''Get Wi-Fi link status'''
    rsp   = [
        status(),
        uint32("link_up", doc='Wi-Fi link status'),
    ]

