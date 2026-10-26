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

**Order of events (inferred from the timestamps, not observed directly):** the certificate was issued at 01:01 UTC, about 33 minutes *before* port 443 was opened at 01:34 UTC. That fits Let's Encrypt's HTTP-01 challenge, which proves control of the domain over port 80, already open, so 443 only had to be opened afterward to serve the site over HTTPS.
