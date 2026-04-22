

# Group he\_wifi



[**Modules**](modules.md) **>** [**he\_wifi**](group__he__wifi.md)



_Functions for managing Wi-Fi connectivity._ 






































## Public Functions

| Type | Name |
| ---: | :--- |
|  int | [**he\_wifi\_connect**](#function-he_wifi_connect) (const char \* ssid, const char \* password) <br>_Connect to a Wi-Fi access point._  |
|  float | [**he\_wifi\_get\_rssi**](#function-he_wifi_get_rssi) (void) <br>_Get the current RSSI (Received Signal Strength Indicator)._  |
|  int | [**he\_wifi\_init**](#function-he_wifi_init) (void) <br>_Initialize the Wi-Fi subsystem._  |




























## Public Functions Documentation




### function he\_wifi\_connect 

_Connect to a Wi-Fi access point._ 
```
int he_wifi_connect (
    const char * ssid,
    const char * password
) 
```





**Parameters:**


* `ssid` Service Set Identifier of the AP. 
* `password` Security key for the network. 



**Returns:**

0 on connection success. 





        

<hr>



### function he\_wifi\_get\_rssi 

_Get the current RSSI (Received Signal Strength Indicator)._ 
```
float he_wifi_get_rssi (
    void
) 
```





**Returns:**

Signal strength in dBm. 





        

<hr>



### function he\_wifi\_init 

_Initialize the Wi-Fi subsystem._ 
```
int he_wifi_init (
    void
) 
```





**Returns:**

0 on success, non-zero error code otherwise. 





        

<hr>

------------------------------


