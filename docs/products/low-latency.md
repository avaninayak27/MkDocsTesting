# Low Latency SoC

The **Talaria Low Latency** variant is optimized for real-time control applications where deterministic response times are critical.

## Key Features

- **Ultra-Fast Wakeup:** < 100μs from deep sleep to active radio.
- **Priority Queueing:** Hardware-level packet prioritization for control loops.
- **Deterministic Latency:** Guaranteed sub-millisecond round-trip times.

{% if extra.internal %}
!!! internal "Engineering Note"
    This product is currently in the "Experimental" phase. 
    Validation testing shows 85μs latency in ideal conditions.
{% endif %}
