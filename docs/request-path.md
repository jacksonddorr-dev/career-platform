# Request path: entering jacksoncareer.me in a browser

Drawn 2026-10-20 as a midterm study reference, from the repository's records (`docs/superpowers/plans/2026-10-01-operate-the-vm.md`, `scripts/start.sh`, `README.md`, `docs/evidence/dns-before-zoho.md`). Anything marked `?` or "unknown" isn't confirmed by the repository.

Unverified: the home network devices and addresses (no Exercise 01 evidence in the repo), and whether the NSG has a TCP 443 rule (the 2026-10-08 record lists only 22 and 80).

## 1. Azure, end to end

```mermaid
flowchart TB
  NOTE["Assumptions: no cached DNS answer · new TCP connection · browser tries http://, gets 301, follows to https://"]

  subgraph HOME["Home LAN · private addresses (exact values unverified)"]
    LAP["Laptop · browser<br/>you type jacksoncareer.me<br/>Wi-Fi interface<br/>private IP, subnet, gateway, DNS server all come from DHCP"]
    AP["Access point<br/>joins Wi-Fi devices to the LAN"]
    SW["Switch<br/>connects devices inside the LAN"]
    RT["Router = default gateway<br/>forwards between networks<br/>NAT: private source → one public IP<br/>stateful firewall · DHCP server"]
    ONT["Modem / fiber box (ONT)"]
  end
  BOX{{"AP + switch + router + NAT + firewall + DHCP<br/>are often one home box — check yours"}}

  ISP["ISP network (details unknown)"]
  NET["Internet routers"]

  subgraph DNS["DNS · a separate exchange BEFORE the web request"]
    RES["Resolver<br/>(address from DHCP; provider unknown)"]
    CF["Cloudflare authoritative nameservers<br/>austin / may.ns.cloudflare.com"]
  end

  subgraph AZ["Azure · North Central US"]
    NSG["NSG vm-career-platform-nsg<br/>TCP 22 from laptop /32 only<br/>TCP 80 from any<br/>TCP 443 ? (no rule recorded — verify)"]
    subgraph VM["VM vm-career-platform · public 52.159.85.45 → private 172.16.0.4"]
      NGX["nginx :80 and :443<br/>80 → 301 to https<br/>TLS ENDS HERE (Let's Encrypt cert)"]
      UV["uvicorn · 2 workers · systemd service<br/>listens on 127.0.0.1:8000 only"]
      DB[("SQLite file<br/>career_platform.db")]
    end
  end

  RESP["5 · Response returns the same path; router NAT maps it back to the laptop<br/>6 · Browser renders HTML, then makes separate requests for CSS, JS, images"]

  LAP ---|Wi-Fi| AP --- SW --- RT --- ONT --- ISP --- NET
  BOX -.- RT

  LAP -. "1 · DNS query, UDP 53<br/>client: laptop → server: resolver" .-> RES
  RES -. "recursive lookup" .-> CF
  CF -. "A 52.159.85.45" .-> RES
  RES -. "answer, cached for TTL" .-> LAP

  NET -- "2 · TCP to 52.159.85.45:443<br/>source = home public IP after NAT" --> NSG
  NSG -- "3 · TLS handshake: browser checks hostname, dates, chain<br/>client: browser → server: nginx" --> NGX
  NGX -- "4 · plain HTTP over loopback<br/>client: nginx → server: uvicorn" --> UV
  UV -- "SQL to a local file, no network" --> DB
  NGX -.- RESP
```

## 2. What changes on Railway

```mermaid
flowchart LR
  LAP2["Laptop<br/>same home path: AP → switch → router/NAT → ONT → ISP → internet"]
  CF2["Cloudflare DNS<br/>apex CNAME, DNS only (not proxied)<br/>flattened → lookup returns Railway edge A records"]

  subgraph RW["Railway · project prolific-enthusiasm · production"]
    EDGE["Railway edge<br/>TLS ENDS HERE (Railway-issued cert)<br/>internals unknown"]
    APP["career-platform service<br/>uvicorn · 2 workers · $PORT = 8080<br/>--proxy-headers: learns the original request was https"]
    PG[("Postgres service<br/>reached via DATABASE_URL on the private network")]
  end

  GONE["Gone vs. Azure: NSG rules, nginx, systemd, SSH, SQLite file<br/>Still yours: code, config/secrets, data, DNS"]

  LAP2 -. "1 · DNS via resolver, UDP 53" .-> CF2
  LAP2 -- "2–3 · TCP 443 + TLS<br/>client: browser → server: edge" --> EDGE
  EDGE -- "4 · plain HTTP + X-Forwarded-Proto<br/>client: edge → server: app" --> APP
  APP -- "SQL over TCP, private network<br/>client: app → server: Postgres" --> PG
  RW -.- GONE
```
