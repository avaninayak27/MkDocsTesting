# Tags Demonstration
This page shows how MkDocs handles content for different audiences using conditional macros.

## Common Content
This paragraph is **Public** and visible to everyone. It contains general product information.

{% if internal %}
## Internal-Only Engineering Data
> [!CAUTION] INTERNAL ONLY
> **Confidential**: This section contains sensitive engineering data about chip internals. 
> It is only visible when building with the `internal=true` flag.
{% endif %}

{% if not internal %}
## Public-Only Customer Data
> [!TIP] CUSTOMER NOTICE
> **Welcome, Customer!**: This section contains helpful tips specifically for end-users. 
> It is only visible when building with the `internal=false` flag.
{% endif %}

## Summary
Documentation is generated from one source but tailored for two different audiences.
