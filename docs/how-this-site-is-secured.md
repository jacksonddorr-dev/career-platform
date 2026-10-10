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


