# Official configuration references checked by root

Checked UTC: 2026-10-09T03:54:51.885279+00:00

- https://nginx.org/en/docs/http/ngx_http_headers_module.html : current primary reference states add_header is inherited only where no add_header exists at the current level; add_header_inherit appeared in 1.29.3. This supports a source-based inference for the declared 1.27 config, not observed runtime header loss. No newer-only directive should be introduced as a fix for a 1.27 image.
- https://docs.docker.com/reference/compose-file/services/#ports : official Compose ports reference distinguishes host-address binding. Actual host reachability/firewall is not established by the reviewed mapping.

No server/container/production execution. Root source-review result agrees with qualified abdd435c and queues an exact runtime matrix; no claim of a tenant bypass or competitor security.
