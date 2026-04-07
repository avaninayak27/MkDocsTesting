# Yo — High-Performance Edge Computing SoC

The **Yo** is InnoPhase IoT's high-performance SoC designed for edge AI and gateway applications requiring significant compute power alongside wireless connectivity.

--8<-- "snippets/t6-summary.md"

## Key Specifications

| Parameter | Value |
| :--- | :--- |
| Frequency | 2.4 GHz / 5 GHz / 6 GHz |
| Wi-Fi Standard | 802.11be (Wi-Fi 7) |
| BLE | Bluetooth 5.4 |
| CPU | Dual-core Arm Cortex-M33 @ 240 MHz |
| RAM | 2 MB SRAM |
| Flash | 16 MB embedded |
| Package | BGA-144 |

## Getting Started

1. Install [Green Tea Studio™](../common/platform.md)
2. Connect the Yo evaluation board via USB-C
3. Flash the default firmware: `gts flash --target yo --image default.bin`

## Shared Platform Features

The Yo includes all [Common Platform](../common/platform.md) capabilities, plus:

- Wi-Fi 7 with MLO (Multi-Link Operation)
- Edge AI accelerator (TinyML inference)
- USB 2.0 host/device
- Ethernet MAC interface

{% if extra.internal %}
## Internal: Yo Development Notes

> [!CAUTION] ENGINEERING ONLY
> **Yo is pre-silicon.** All specifications are based on RTL simulation. Do not share power numbers externally — final silicon measurements will differ by ±15%. Tape-out scheduled for Q4 2026.
{% endif %}
