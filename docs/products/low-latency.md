# Low Latency

## Overview

Low latency is a critical requirement for real-time wireless communication systems. InnoPhase IoT's architecture is designed to minimize end-to-end latency across the entire signal processing chain.

## Key Features

- **Ultra-fast wake-up times**: Transition from deep sleep to active mode in microseconds.
- **Optimized MAC layer**: Streamlined MAC processing reduces per-packet overhead.
- **Hardware-accelerated processing**: Dedicated hardware blocks handle time-critical operations without CPU intervention.

## Applications

| Application | Typical Latency Requirement |
|---|---|
| Industrial IoT Control | < 10 ms |
| Audio Streaming | < 20 ms |
| Sensor Data Aggregation | < 50 ms |
| Real-time Location | < 5 ms |

## Configuration

To enable low-latency mode, configure the following parameters in your firmware build:

```c
// Enable low-latency optimizations
#define CONFIG_LOW_LATENCY_MODE  1
#define CONFIG_WAKE_INTERVAL_US  500
```

!!! note
    Low-latency mode may increase average power consumption. Consider your power budget when enabling this feature.
