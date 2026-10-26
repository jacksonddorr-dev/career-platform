# Final DNS records — jacksoncareer.me

Date: **2026-10-26** (records listed 00:47 UTC, public answers checked 00:49 UTC). This is the state after Zoho Mail (2026-10-13) and the `www` redirect fix (2026-10-26, `docs/evidence/www-redirect.md`). The earlier state is in `docs/evidence/dns-before-zoho.md`.

## Delegation

The domain is registered at Namecheap. The `.me` registry delegates it to Cloudflare, so Cloudflare's nameservers are authoritative for every record below.

```
$ dig +trace +nodnssec NS jacksoncareer.me
jacksoncareer.me.  3600   IN NS  austin.ns.cloudflare.com.   ;; from b0.nic.me (the .me registry)
jacksoncareer.me.  3600   IN NS  may.ns.cloudflare.com.
jacksoncareer.me.  86400  IN NS  austin.ns.cloudflare.com.   ;; from may.ns.cloudflare.com
jacksoncareer.me.  86400  IN NS  may.ns.cloudflare.com.
```

## Records

Listed with `cf dns records list -z jacksoncareer.me --order type`. TTL is "Auto" for all of them.

| Type | Name | Value | Proxy | Created | Purpose |
|---|---|---|---|---|---|
| CNAME | `jacksoncareer.me` | `ctxkvml3.up.railway.app` | DNS only | 2026-10-11 | Sends the site to Railway. Cloudflare flattens a CNAME at the root, so lookups get Railway's A record. DNS only, so the browser connects straight to Railway and Railway's certificate. |
| A | `www.jacksoncareer.me` | `192.0.2.1` | **Proxied** | 2026-10-13 (changed 2026-10-26) | Placeholder so Cloudflare answers `www`. A redirect rule sends every `www` request to `https://jacksoncareer.me` with a 301. The address is never contacted. |
| TXT | `_railway-verify.jacksoncareer.me` | `railway-verify=96c5…` | DNS only | 2026-10-11 | Proves to Railway that I control the domain, so it attaches the custom domain and issues the certificate. Keep it. |
| MX 10 | `jacksoncareer.me` | `mx.zoho.com` | DNS only | 2026-10-13 | Where other mail servers deliver mail for `@jacksoncareer.me`. The lowest number is tried first. |
| MX 20 | `jacksoncareer.me` | `mx2.zoho.com` | DNS only | 2026-10-13 | Backup mail server. |
| MX 50 | `jacksoncareer.me` | `mx3.zoho.com` | DNS only | 2026-10-13 | Second backup mail server. |
| TXT | `jacksoncareer.me` | `v=spf1 include:zohomail.com ~all` | DNS only | 2026-10-13 | SPF: lists Zoho's servers as allowed to send mail for the domain. `~all` marks other senders as suspicious (soft fail). |
| TXT | `zmail._domainkey.jacksoncareer.me` | `v=DKIM1; k=rsa; p=…` (public key left out) | DNS only | 2026-10-13 | DKIM: the public key receivers use to check Zoho's signature on my outgoing mail. |
| TXT | `_dmarc.jacksoncareer.me` | `v=DMARC1; p=none; rua=mailto:jackson@jacksoncareer.me` | DNS only | 2026-10-13 | DMARC: tells receivers what to do when SPF/DKIM don't line up with the From domain. `p=none` means only report; aggregate reports go to my Zoho mailbox. |
| TXT | `jacksoncareer.me` | `zoho-verification=zb00946502.zmverify.zoho.com` | DNS only | 2026-10-13 | Proved domain ownership to Zoho during mail setup. |

MX and TXT records can't be proxied. Only the site records (root and `www`) have a proxy choice.

## What the public sees

Checked through `1.1.1.1` at 2026-10-26 00:49:57 UTC:

| Query | Answer |
|---|---|
| `NS jacksoncareer.me` | `austin.ns.cloudflare.com.`, `may.ns.cloudflare.com.` |
| `A jacksoncareer.me` | `69.46.46.38`, the same as `A ctxkvml3.up.railway.app` (flattened CNAME) |
| `A www.jacksoncareer.me` | `172.67.142.71`, `104.21.71.21` (Cloudflare's edge, because it's proxied) |
| `MX jacksoncareer.me` | `10 mx.zoho.com.`, `20 mx2.zoho.com.`, `50 mx3.zoho.com.` |
| `TXT jacksoncareer.me` | the SPF and `zoho-verification` values above |
| `TXT _dmarc.jacksoncareer.me` | the DMARC value above |
| `TXT zmail._domainkey.jacksoncareer.me` | starts `v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBA…` |
| `TXT _railway-verify.jacksoncareer.me` | starts `railway-verify=96c5004e776173…` |

Every record in Cloudflare matches what public resolvers return.

## Changes since the pre-Zoho snapshot (2026-10-13)

- Added the three MX records and the SPF, DKIM, DMARC, and `zoho-verification` TXT records (2026-10-13).
- `www` changed from a DNS-only CNAME to Railway, to a DNS-only A record to the Azure VM (`52.159.85.45`, 2026-10-13 22:25 UTC), then to a proxied placeholder with the redirect (2026-10-26). The VM was deleted at 23:03 UTC on 2026-10-13, so `www` didn't work between then and the fix.
