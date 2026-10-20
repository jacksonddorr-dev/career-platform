# Request path: entering jacksoncareer.me in a browser

Drawn 2026-10-20 as a midterm study reference, from the repository's records (`docs/superpowers/plans/2026-10-01-operate-the-vm.md`, `scripts/start.sh`, `README.md`, `docs/evidence/dns-before-zoho.md`). Anything marked `?` or "unknown" isn't confirmed by the repository.

**Assumptions:** no cached DNS answer, a new TCP connection, and the browser tries `http://jacksoncareer.me` first and follows the 301 to `https://jacksoncareer.me`.

**Unverified:** the home network devices and addresses (no Exercise 01 evidence in the repo), and whether the NSG has a TCP 443 rule (the 2026-10-08 record lists only 22 and 80).

## 1. Azure

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
    NSG["NSG<br/>22: laptop only<br/>80: any · 443: ?"]
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

  LAP <-. "1 · jacksoncareer.me?<br/>→ Railway edge IPs" .-> CF
  LAP --> PATH -- "2 · TCP 443<br/>3 · TLS" --> EDGE -- "4 · HTTP +<br/>X-Forwarded-Proto" --> APP -- SQL --> PG
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
