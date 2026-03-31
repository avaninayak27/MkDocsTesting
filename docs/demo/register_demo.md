# Register Demo: SYSTEM_CONFIG
This page demonstrates how MkDocs handles complex bit-field tables using a mix of Markdown and HTML.

## Register: 0x40004000 (SYS_CFG)
| Bit | Name | Type | Reset | Description |
| :--- | :--- | :--- | :--- | :--- |
| 31:16 | RESERVED | - | 0x0000 | - |
| 15:8 | MODE | RW | 0x01 | See Mode Table below |
| 7:0 | STATUS | RO | 0xAF | Device status flags |

### Detailed Mode Configuration
Standard Markdown cannot span rows, so we use HTML for this complex section:

<table>
  <thead>
    <tr>
      <th rowspan="2">Mode ID</th>
      <th colspan="2">Capability</th>
      <th rowspan="2">Description</th>
    </tr>
    <tr>
      <th>Wi-Fi</th>
      <th>BLE</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>0x01</td>
      <td>Dual</td>
      <td>Enabled</td>
      <td>Standard operation mode with both radios active.</td>
    </tr>
    <tr>
      <td>0x02</td>
      <td>Single</td>
      <td>Disabled</td>
      <td>Power-saving mode for Wi-Fi only tasks.</td>
    </tr>
  </tbody>
</table>

{% if internal %}
## Internal Engineering Data
> [!CAUTION] INTERNAL ONLY: DO NOT PUBLISH
> **Register 0x40004004 (INTERNAL_DEBUG):**
> - Bit 0: FORCE_RESET (Self-destruct sequence for test chips).
> - Bit 1: DEBUG_UART_ENABLE (High power consumption).

*This section is automatically stripped from consumer-facing manuals.*
{% endif %}
