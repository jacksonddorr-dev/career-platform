# www → root redirect (Cloudflare)

Date: **2026-10-26** (UTC). Zone `jacksoncareer.me` on Cloudflare's Free plan. Changes and checks were run from my laptop with the Cloudflare CLI (`cf`), `curl`, `dig`, and `openssl`.

## Before

| Record | Value | Proxied | Created |
|---|---|---|---|
| `jacksoncareer.me` CNAME | `ctxkvml3.up.railway.app` (Railway) | No | — |
| `www.jacksoncareer.me` A | `52.159.85.45` (Azure VM) | **No** | 2026-10-13 22:25:56 UTC |

A redirect rule already existed, created 2026-10-13 22:22:29 UTC from Cloudflare's "Redirect from WWW to root domain" template:

- **When:** `http.request.full_uri wildcard r"http*://www.*"`
- **Then:** 301 to `wildcard_replace(http.request.full_uri, r"http*://www.*", r"https://${2}")`, so the path and query string are kept

**Why `www` was broken:** redirect rules only run on traffic that passes through Cloudflare's proxy. The `www` record was DNS only, so browsers went straight to `52.159.85.45`, and that VM had been deleted at 23:03 UTC the same day (`docs/superpowers/plans/2026-10-01-operate-the-vm.md`, section 5). The rule never ran.

## Change (2026-10-26 00:46:16 UTC)

```
cf dns records edit <www record id> -z <zone id> --body '{"type":"A","name":"www.jacksoncareer.me","content":"192.0.2.1","proxied":true,"ttl":1,...}'
```

`www` is now an A record to `192.0.2.1`, **proxied**. `192.0.2.1` is a reserved documentation address. Cloudflare never forwards to it, because the redirect rule answers every `www` request first. The redirect rule wasn't changed. The root record stays DNS only, so Railway keeps issuing and renewing its certificate.

## Verification (2026-10-26 00:46 UTC)

**DNS:** `www` now resolves to Cloudflare's edge (`104.21.71.21`, `172.67.142.71`) from the authoritative nameserver, from `1.1.1.1`, and from my local resolver.

**Redirects** (`curl -sS -I -L`):

```
== http://www.jacksoncareer.me/
HTTP/1.1 301 Moved Permanently
Location: https://jacksoncareer.me/
Server: cloudflare
HTTP/2 405
server: railway-hikari
final (GET): 200 https://jacksoncareer.me/ ssl_verify=0

== https://www.jacksoncareer.me/
HTTP/2 301
location: https://jacksoncareer.me/
server: cloudflare
HTTP/2 405
server: railway-hikari
final (GET): 200 https://jacksoncareer.me/ ssl_verify=0

== https://www.jacksoncareer.me/projects?x=1
HTTP/2 301
location: https://jacksoncareer.me/projects?x=1
```

Both `http://www` and `https://www` reach `https://jacksoncareer.me/` in one 301, and the path and query string survive. The `405` lines come from `curl -I` sending a HEAD request, which the app's GET-only routes reject. The same URLs fetched with GET return 200 (the `final` lines).

**Certificates** (`openssl s_client -servername <host>`):

| Host | Served by | Subject / SAN | Issuer | Valid | Verify |
|---|---|---|---|---|---|
| `www.jacksoncareer.me` | Cloudflare edge (Universal SSL) | `CN=jacksoncareer.me`; SAN `*.jacksoncareer.me`, `jacksoncareer.me` | Let's Encrypt `YE2` | 2026-10-01 21:01:05 to 2026-12-30 21:01:04 GMT | `0 (ok)` |
| `jacksoncareer.me` | Railway | `CN=jacksoncareer.me`; SAN `jacksoncareer.me` | Let's Encrypt `YE1` | 2026-10-11 01:07:07 to 2027-01-09 01:07:06 GMT | `0 (ok)` |

Cloudflare and Railway each renew their own certificate automatically. I didn't observe a renewal.

## Undo

Set the `www` record back to DNS only (the redirect would stop), or delete the redirect rule. The before state is in the table above.
