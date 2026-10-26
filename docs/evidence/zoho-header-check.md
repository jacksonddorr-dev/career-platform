# Zoho header check — reply from jackson@jacksoncareer.me

Checked 2026-10-25 (PDT) in Gmail with **Show original**. The message body and my Gmail address are left out.

## The message

| Field | Value |
|---|---|
| Subject | `Re: Test 01: inbound` (a reply from Zoho webmail to the 2026-10-13 inbound test) |
| From | `jackson@jacksoncareer.me`, "Using Zoho Mail" |
| To | `<gmail>` |
| Message-ID | `<1a1760e1548.a8e6652297020.2671664298261600750@jacksoncareer.me>` |
| Created | Sun, Oct 25, 2026 at 7:33 PM PDT (2026-10-26 02:33 UTC), delivered after 5 seconds |

## Gmail's summary

```
SPF:    PASS with IP 165.173.180.52
DKIM:   'PASS' with domain jacksoncareer.me
DMARC:  'PASS'
```

## Authentication-Results (added by mx.google.com)

```
Authentication-Results: mx.google.com;
       dkim=pass header.i=@jacksoncareer.me header.s=zmail header.b=Ou2A24cW;
       arc=pass (i=1 spf=pass spfdomain=jacksoncareer.me dkim=pass dkdomain=jacksoncareer.me dmarc=pass fromdomain=jacksoncareer.me);
       spf=pass (google.com: domain of jackson@jacksoncareer.me designates 165.173.180.52 as permitted sender) smtp.mailfrom=jackson@jacksoncareer.me;
       dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=jacksoncareer.me
```

## What each check decided

| Check | Result | What it checked | Domain it named |
|---|---|---|---|
| SPF | **pass** | Whether the sending server, `165.173.180.52`, is allowed to send for the envelope sender's domain. My SPF record (`v=spf1 include:zohomail.com ~all`) authorizes Zoho's servers. | Envelope sender: `smtp.mailfrom=jackson@jacksoncareer.me` |
| DKIM | **pass** | Whether the signature in the header matches the public key published at the `zmail` selector, so the signed parts weren't changed after Zoho signed them | `header.i=@jacksoncareer.me`, selector `header.s=zmail` |
| DMARC | **pass** | Whether SPF or DKIM passed for a domain that matches the visible From domain (alignment). Both did. | `header.from=jacksoncareer.me` |

- `p=NONE` is my DMARC policy (monitor only). `dis=NONE` means Google took no action against the message. It would have reported a failure, not blocked it.
- The `arc=pass` entry is an ARC seal (instance `i=1`) recording the same three results. The header doesn't show which hop added it.
- Each check names a different part of the message: SPF the envelope sender, DKIM the signing domain and selector, DMARC the From header. DMARC passes because those domains line up with `jacksoncareer.me`.

## Not covered here

- This is one message, a reply. The new outgoing message (`Test 06: new outbound`, 2026-10-19) is tracked in `docs/evidence/ex06.md`.
- `165.173.180.52` being a Zoho server is Google's conclusion from my SPF record. I didn't look the address up separately.

**My prediction before opening the header, in my own words:**

&nbsp;
