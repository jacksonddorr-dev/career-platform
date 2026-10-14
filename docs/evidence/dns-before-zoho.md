# DNS before Zoho Mail — jacksoncareer.me

Snapshot taken **2026-10-13**, before adding any Zoho Mail records.

- Zone: `jacksoncareer.me` (status: active, type: full)
- Nameservers: `austin.ns.cloudflare.com`, `may.ns.cloudflare.com`
- Command: `cf dns records list -z jacksoncareer.me --order type` (Cloudflare CLI 1.0.0-beta.14)
- Total records: **3**

| Type  | Name                               | Content                                                                                   | TTL  | Proxied |
|-------|------------------------------------|-------------------------------------------------------------------------------------------|------|---------|
| CNAME | `jacksoncareer.me`                 | `ctxkvml3.up.railway.app`                                                                 | Auto | No      |
| CNAME | `www.jacksoncareer.me`             | `ctxkvml3.up.railway.app`                                                                 | Auto | No      |
| TXT   | `_railway-verify.jacksoncareer.me` | `"railway-verify=96c5004e776173b3e685a77e1ce61ae5f72e51bd02db821c01f29386b9c1a9c7"`       | Auto | No      |

## Notes

- There are no MX, SPF, DKIM or DMARC records yet, so the domain currently has no mail setup.
- The apex is a CNAME, which works through Cloudflare CNAME flattening. Zoho's MX and TXT records can go at the apex next to it.
