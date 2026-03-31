# Ne — Multi-Protocol Wi-Fi + BLE SoC

The **Ne** is InnoPhase IoT's multi-protocol SoC combining Wi-Fi and Bluetooth Low Energy for connected devices requiring dual-radio capability.

## Key Specifications

| Parameter | Value |
| :--- | :--- |
| Frequency | 2.4 GHz / 5 GHz |
| Wi-Fi Standard | 802.11a/b/g/n/ac |
| BLE | Bluetooth 5.3 |
| Active Rx Current | 35 mA (Wi-Fi) / 8 mA (BLE) |
| Sleep Current | < 2 µA |
| Flash | 8 MB embedded |
| Package | QFN-56 |

## Getting Started

1. Install [Green Tea Studio™](../common/platform.md)
2. Connect the Ne evaluation board via USB
3. Flash the default firmware: `gts flash --target ne --image default.bin`

## Shared Platform Features

The Ne includes all [Common Platform](../common/platform.md) capabilities, plus:

- Dual-band Wi-Fi radio
- BLE 5.3 with direction finding
- Concurrent Wi-Fi + BLE operation

{% if internal %}
## Internal: Ne Sampling Notes

> [!CAUTION] ENGINEERING ONLY
> **Ne ES1 samples**: BLE direction finding is disabled in firmware. AoA/AoD will be enabled in ES2 samples (ETA: Q3 2026). Do not promise this feature to early-access customers.

{% endif %}
