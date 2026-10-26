# How This Site Is Secured

The certificate: who issued it, which names it covers, and when it expires:

This covers who issued the certificate, the domain name it covers, and when it expires. Let's Encrypt is the certificate authority that issued the certificate. This certificate covers the domain names of jacksoncareer.me and www.jacksoncareer.me. This certificate will expire in 90 days on 01/06/27.


How it renews:


How renewal works and what my renewal test and timer check showed. renewal is automatic and a timer checks twice a day for an expiration date. It renews when needed and proves I still own the domain.


 Which ports are open to the Internet, and why:

which ports are open to the internet and why. The Azure firewall checks every incoming message against connection/security rules. Ports 443 and 80 are open to everyone. Port 22 is only open to my laptop's IP for the SSH. 


 Where encryption starts and where it ends:

Where the encryption starts and ends. Encryption starts in the browser when nginx shows the certificate and the browser makes a check. Encryption ends at nginx and inside the server itself it's unencrypted.


 How a customer could check all this themselves:

How can anyone check the certificate? They can visit the site and click the Icon to check if it is valid


 Evidence: openssl output(run on 10/10/26):

azureuser@vm-career-platform:~$ openssl s_client -connect jacksoncareer.me:443 -servername jacksoncareer.me </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
subject=CN = jacksoncareer.me
issuer=C = US, O = Let's Encrypt, CN = YE2
notBefore=Oct  8 01:01:07 2026 GMT
notAfter=Jan  6 01:01:06 2027 GMT




---

## Addendum: Azure HTTPS setup record (written 2026-10-26, after the VM was deleted)

Everything above is my Exercise 4 write-up and is unchanged. This addendum records what can still be verified about how HTTPS was set up on the Azure VM. The VM and its disk were deleted on 2026-10-13 (see `docs/superpowers/plans/2026-10-01-operate-the-vm.md`, section 5), so some parts can no longer be checked.

| Part | What's known | Source |
|---|---|---|
| NSG rule for 443 | `Allow-HTTPS-443`: inbound, TCP 443, from any source, priority 320, Allow. Created **2026-10-08 01:34:39 UTC** by my account. It still exists. | `az network nsg rule show` and the Azure activity log, both checked 2026-10-26 |
| Certificate | Let's Encrypt (issuer `YE2`), subject `CN = jacksoncareer.me`, valid 2026-10-08 01:01:07 to 2027-01-06 01:01:06 GMT. | `openssl` output above, run 2026-10-10 |
| Before HTTPS | At 2026-10-08 00:43 UTC the NSG allowed only 22 (laptop) and 80 (any). | `docs/superpowers/plans/2026-10-01-operate-the-vm.md`, section 4 |
| nginx and certbot in use | The VM ran "behind nginx + Let's Encrypt for `jacksoncareer.me` and `www`." | `docs/superpowers/plans/2026-10-10-railway-postgres-migration.md`, *Starting state* (inspected 2026-10-10) |
| certbot install and commands | **Not recorded, no longer verifiable.** No plan, commit, or saved output covers it, and the VM is gone. | — |
| nginx 443 server block and the HTTP→HTTPS redirect | **Not recorded, no longer verifiable**, for the same reason. | — |
| Renewal timer and dry run | **Not recorded, no longer verifiable.** The section above describes the twice-daily timer, but no `systemctl list-timers` or `certbot renew --dry-run` output was saved. | — |

**Order of events (corrected 2026-10-26, still inferred):** the certificate's `notBefore` is 01:01:07 UTC, but Let's Encrypt backdates `notBefore` by roughly an hour, so the certificate was most likely issued around 02:00 UTC, *after* port 443 was opened at 01:34:39. Either order works: Let's Encrypt's HTTP-01 challenge proves control of the domain over port 80, which was already open. An earlier version of this note read `notBefore` as the issue time and said the certificate came first; that was wrong.

---

## Addendum: Railway certificate (recorded 2026-10-26)

Since the cutover, `https://jacksoncareer.me` is served by Railway, not by nginx on the VM. This records the certificate the site uses now. The `www` name has a separate Cloudflare certificate, covered in `docs/evidence/www-redirect.md`.

**Evidence: openssl output (run 2026-10-26 00:54 UTC from my laptop):**

```
$ openssl s_client -connect jacksoncareer.me:443 -servername jacksoncareer.me </dev/null 2>/dev/null \
    | openssl x509 -noout -subject -issuer -dates -serial -ext subjectAltName -text
subject=CN=jacksoncareer.me
issuer=C=US, O=Let's Encrypt, CN=YE1
notBefore=Oct 11 01:07:07 2026 GMT
notAfter=Jan  9 01:07:06 2027 GMT
serial=068C82F5E88325AEE34899446B928B597C83
    DNS:jacksoncareer.me
            Public Key Algorithm: id-ecPublicKey
                NIST CURVE: P-256

Certificate chain
 0 s:CN=jacksoncareer.me
   i:C=US, O=Let's Encrypt, CN=YE1
 1 s:C=US, O=Let's Encrypt, CN=YE1
   i:C=US, O=ISRG, CN=Root YE
 2 s:C=US, O=ISRG, CN=Root YE
   i:C=US, O=Internet Security Research Group, CN=ISRG Root X2
 3 s:C=US, O=Internet Security Research Group, CN=ISRG Root X2
   i:C=US, O=Internet Security Research Group, CN=ISRG Root X1
New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384
Verify return code: 0 (ok)
```

| Question | Answer |
|---|---|
| Hostname | `jacksoncareer.me` only (subject and the single SAN entry). It doesn't cover `www`, which is why `www` is handled by Cloudflare's redirect instead. |
| Issuer | Let's Encrypt `YE1`, chaining to ISRG roots. `Verify return code: 0 (ok)` means my laptop trusts the chain. |
| Validity | 2026-10-11 01:07:07 to 2027-01-09 01:07:06 GMT (90 days). It was issued right after the custom domain was added on Railway during the cutover. |
| Key | ECDSA P-256 |
| Who renews it | Railway. Its docs say it issues Let's Encrypt certificates with ECDSA keys for custom domains, "valid for 90 days and automatically renewed when 30 days of validity remain" (https://docs.railway.com/networking/domains/working-with-domains, read 2026-10-26). For this certificate that's around **2026-12-10**. I can't run a renewal test on Railway. The check is to rerun the openssl command after 2026-12-10 and expect a new `notBefore` date. |
| What renewal depends on | The root record staying **DNS only** and pointing at Railway, plus the `_railway-verify` TXT record. Railway's docs warn it may not be able to issue a certificate for a proxied (orange-cloud) domain. |
| Where encryption ends | At Railway's edge. Railway forwards plain HTTP to the app on port 8080, which is why `scripts/start.sh` runs uvicorn with `--proxy-headers`. On Azure it ended at nginx on the VM. |

**Hostname selection (SNI):** Railway's edge serves many sites on the same address, and picks the certificate by the name the browser sends. Asking the same address for a different name returns Railway's shared certificate instead:

```
$ openssl s_client -connect jacksoncareer.me:443 -servername wrong.example | openssl x509 -noout -subject
subject=CN=*.up.railway.app
```
