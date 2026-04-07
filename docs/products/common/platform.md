# Common Platform

The Talaria common platform provides the foundation for all InnoPhase IoT products (He, Ne, Yo).

## Wi-Fi Subsystem

The integrated Wi-Fi 7 radio supports:

- 802.11a/b/g/n/ac/ax/be
- 2.4 GHz and 5 GHz dual-band operation
- Ultra-low-power modes (< 1 mA in connected standby)

## Security Engine

All products include a hardware-accelerated security engine:

- AES-128/256 encryption
- SHA-256 hashing
- TrustZone secure boot
- Secure key storage (OTP)

## Green Tea Studio™ (GTS)

GTS is the unified development environment for all Talaria products. It includes:

- Eclipse-based IDE
- Real-time debugging
- Over-the-air (OTA) update framework
- Power profiler

{% if extra.internal %}
## Internal: Platform Errata

> [!CAUTION] ENGINEERING ONLY
> **Known Issue (PLT-2847)**: The Wi-Fi radio draws 2.3 mA in standby on A0 silicon. Workaround: Set register 0x40004008[3] = 1 before entering sleep mode. Fixed in B0 silicon.

{% endif %}
