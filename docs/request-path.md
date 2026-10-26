# Architecture diagrams

The web request path on Azure (historical) and on Railway (current), plus the email and analytics paths. Diagrams 1–2 were drawn 2026-10-20 as a midterm study reference; diagrams 3–4 and the `www` redirect were added 2026-10-26. All are drawn from the repository's records (`docs/superpowers/plans/2026-10-01-operate-the-vm.md`, `scripts/start.sh`, `README.md`, `docs/evidence/dns-before-zoho.md`). Anything marked `?` or "unknown" isn't confirmed by the repository.

**Assumptions:** no cached DNS answer, a new TCP connection, and the browser tries `http://jacksoncareer.me` first and follows the 301 to `https://jacksoncareer.me`.

**Unverified:** the home network devices and addresses (no Exercise 01 evidence in the repo). The NSG's TCP 443 rule, unknown when this was first drawn, was confirmed on 2026-10-26: `Allow-HTTPS-443`, created 2026-10-08 01:34 UTC (`docs/how-this-site-is-secured.md`, Azure addendum).

## 1. Azure (2026-09-29 to 2026-10-11; VM deleted 2026-10-13)

```mermaid
flowchart LR
  subgraph HOME["Home LAN · private IPs · often one box"]
    LAP["Laptop browser<br/>jacksoncareer.me<br/>private IP from DHCP"]
    AP["Access point"]
    SW["Switch"]
    RT["Router = gateway<br/>NAT · firewall · DHCP"]
  end
  ONT["Modem / ONT"]
  ISP["ISP<br/>(unknown)"]
  NET["Internet"]

  subgraph DNS["Step 1 · DNS lookup, separate and first"]
    RES["Resolver<br/>(unknown)"]
    CF["Cloudflare nameservers<br/>for jacksoncareer.me"]
  end

  subgraph AZ["Azure"]
    NSG["NSG<br/>22: laptop only<br/>80 and 443: any"]
    subgraph VM["VM · 52.159.85.45 → 172.16.0.4"]
      NGX["nginx :443<br/>cert for jacksoncareer.me<br/>TLS ends here"]
      UV["uvicorn × 2<br/>127.0.0.1:8000"]
      DB[("SQLite file")]
    end
  end

  LAP <-. "jacksoncareer.me?<br/>→ 52.159.85.45<br/>UDP 53" .-> RES <-.-> CF

  LAP -- "Wi-Fi" --> AP --> SW --> RT -- "public IP<br/>after NAT" --> ONT --> ISP --> NET
  NET -- "2 · TCP 443" --> NSG -- "3 · TLS" --> NGX -- "4 · HTTP" --> UV -- SQL --> DB
```

## 2. What changes on Railway

```mermaid
flowchart LR
  LAP["Laptop browser<br/>jacksoncareer.me"]
  PATH["Same home LAN,<br/>NAT, ISP, internet"]
  CF["Cloudflare DNS<br/>jacksoncareer.me CNAME<br/>DNS only, flattened"]

  subgraph RW["Railway"]
    EDGE["Railway edge<br/>cert for jacksoncareer.me<br/>TLS ends here"]
    APP["App · uvicorn × 2<br/>$PORT 8080"]
    PG[("Postgres<br/>private network")]
  end

  CFE["Cloudflare edge<br/>www.jacksoncareer.me (proxied)<br/>cert for *.jacksoncareer.me"]

  LAP <-. "1 · jacksoncareer.me?<br/>→ Railway edge IPs" .-> CF
  LAP --> PATH -- "2 · TCP 443<br/>3 · TLS" --> EDGE -- "4 · HTTP +<br/>X-Forwarded-Proto" --> APP -- SQL --> PG
  PATH -. "www: HTTP 80 / HTTPS 443" .-> CFE -. "301 to https://jacksoncareer.me/…" .-> LAP
```

**Gone vs. Azure:** NSG rules, nginx, systemd, SSH, the SQLite file. **Still yours:** code, config and secrets, data, DNS.

## Steps

| Step | Client → server | Protocol and port | Azure | Railway |
|---|---|---|---|---|
| 1 | Laptop → resolver → Cloudflare | DNS, UDP 53 | Answer `52.159.85.45` | Root CNAME flattened, answer is Railway edge IPs |
| 2 | Browser → web entry | TCP 443 | NSG lets it reach nginx | Railway edge |
| 3 | Browser → web entry | TLS: browser checks hostname `jacksoncareer.me`, dates, chain | Ends at nginx (Let's Encrypt) | Ends at Railway's edge (Railway-issued cert) |
| 4 | Web entry → app | Plain HTTP | nginx → `127.0.0.1:8000` | Edge → app on 8080; `--proxy-headers` tells it the request was https |
| 4b | App → database | SQL | Local file, no network | Postgres over Railway's private network |
| 5 | Response | Same path back | Router NAT maps the reply to the laptop | Same |
| 6 | Browser | New HTTP requests | CSS, JS, images | Same |

## 3. Email (Zoho Mail, since 2026-10-13)

```mermaid
flowchart LR
  subgraph OUT["Outside sender / receiver"]
    GM["Gmail"]
  end
  subgraph CFD["Cloudflare DNS · jacksoncareer.me"]
    MX["MX 10 mx · 20 mx2 · 50 mx3 .zoho.com"]
    SPF["TXT SPF<br/>v=spf1 include:zohomail.com ~all"]
    DKIM["TXT zmail._domainkey<br/>DKIM public key"]
    DMARC["TXT _dmarc<br/>p=none · reports to jackson@"]
  end
  subgraph ZO["Zoho Mail"]
    ZMX["Zoho MX servers"]
    BOX["Mailbox<br/>jackson@jacksoncareer.me"]
    ZOUT["Zoho outgoing server<br/>(e.g. 165.173.180.52)<br/>signs with DKIM selector zmail"]
  end
  ME["Me · browser<br/>Zoho webmail"]

  GM -. "Inbound 1 · DNS: MX for jacksoncareer.me?" .-> MX
  GM -- "Inbound 2 · SMTP, TCP 25" --> ZMX --> BOX
  ME -- "HTTPS 443" --> BOX
  BOX --> ZOUT -- "Outbound · SMTP, TCP 25" --> GM
  GM -. "checks SPF (IP allowed?)" .-> SPF
  GM -. "checks DKIM signature" .-> DKIM
  GM -. "DMARC: SPF/DKIM aligned with From?" .-> DMARC
```

Inbound mail never touches Railway or the site: the MX records send it straight to Zoho. For outbound mail, Gmail looks up my SPF, DKIM, and DMARC records in Cloudflare DNS and decides whether to trust the message. On 2026-10-25 all three passed for `jacksoncareer.me` (`docs/evidence/zoho-header-check.md`). The SMTP port between mail servers (25) is the standard one. I didn't observe it directly.

## 4. Analytics (GA4)

```mermaid
flowchart LR
  B["Visitor's browser"]
  RW["Railway app<br/>serves the HTML<br/>with consent banner"]
  GTM["www.googletagmanager.com<br/>gtag.js"]
  GA["google-analytics.com<br/>/g/collect"]
  RT["GA4 property G-XWCRC21WXW<br/>Realtime · reports"]

  RW -- "1 · HTTPS 443: page<br/>(consent default: denied)" --> B
  B -- "2 · only after Allow:<br/>HTTPS 443, load gtag.js" --> GTM
  B -- "3 · HTTPS 443: page_view,<br/>click (outbound)" --> GA --> RT
```

Analytics events go from the visitor's browser straight to Google. They never pass through Railway, so the app's logs don't show them. Before the visitor clicks **Allow analytics**, nothing is loaded from Google (Consent Mode default `denied`). On 2026-10-25 Realtime showed `page_view` and an outbound `click` to LinkedIn (`docs/evidence/ex06.md`, section 3). The collection hostname is shown generically; I didn't capture the exact host in the Network tab.

