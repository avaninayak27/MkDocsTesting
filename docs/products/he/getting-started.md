# He — Ultra-Low-Power Wi-Fi SoC

The **He** is InnoPhase IoT's flagship ultra-low-power Wi-Fi SoC, designed for battery-operated IoT sensors and smart home devices.

--8<-- "docs/snippets/t6-summary.md"

For an overview, please refer to the [Introduction](Introduction.md).


## Key Specifications

| Parameter | Value |
| :--- | :--- |
| Frequency | 2.4 GHz |
| Wi-Fi Standard | 802.11b/g/n |
| Active Rx Current | 28 mA |
| Sleep Current | < 1 µA |
| Flash | 4 MB embedded |
| Package | QFN-40 |

## Getting Started

1. Install [Green Tea Studio™](../common/platform.md)
2. Connect the He evaluation board via USB
3. Flash the default firmware: `gts flash --target he --image default.bin`

## Shared Platform Features

The He includes all [Common Platform](../common/platform.md) capabilities, including:

- Wi-Fi 7 radio subsystem
- Hardware security engine
- OTA update framework

{% if extra.internal %}
## Internal: He Silicon Notes

> [!CAUTION] ENGINEERING ONLY
> **He A0 Tape-out**: Debug UART is on GPIO[14:15]. Do NOT expose these pins in the customer EVK schematic. B0 moves debug to GPIO[22:23].

{% endif %}
