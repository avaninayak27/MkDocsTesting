# Application Processor Subsystem

This section covers the multi-core application processor (AP) subsystem available in high-end Talaria variants.

## Subsystem Architecture

The AP subsystem consists of:

- Dual-core ARM Cortex-M33 running at 160MHz
- Dedicated DSP for voice and signal processing
- Shared L3 cache and memory controller

{% if extra.internal %}
!!! internal "Technical Detail"
    The DSP uses a proprietary instruction set designed by InnoPhase IoT. 
    Refer to the `DSP_ISA_Reference.pdf` in the internal vault for details.
{% endif %}
