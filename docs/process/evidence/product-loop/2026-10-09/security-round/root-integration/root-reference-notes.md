# Additional official references

Read 9 October 2026. Public technical guidance only; no deployment inspection or
competitor security benchmark.

- [Nginx headers module](https://nginx.org/en/docs/http/ngx_http_headers_module.html):
  location-level add_header declarations normally prevent inheritance from the
  parent. add_header_inherit is available from 1.29.3; do not assume the deployed
  version supports it. Use a version-compatible configuration and actual route
  response checks in the separate bounded header task.
- [OWASP ASVS](https://owasp.org/projects/asvs): published technical verification
  requirements provide a basis for a test plan. A review against selected controls
  is not full ASVS verification, certification or a penetration test. This round
  does not claim any ASVS level.

The current approved full local suite does not include Nginx/container execution.
The Mac has no nginx or docker executable on PATH. This round's five doctor
checks cover the Python/Node dependencies and Chromium; they do not execute
container or Nginx gates. Those checks remain NOT_RUN.
