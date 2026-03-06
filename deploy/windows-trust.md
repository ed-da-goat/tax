# Trusting the Self-Signed Certificate on Windows

The Georgia CPA app uses a self-signed HTTPS certificate. Windows browsers
will show a security warning until you import the certificate into the
Windows trust store.

## Option A: Click Through (easiest, per-session)

1. Open Edge or Chrome on the Windows machine
2. Navigate to `https://<mac-ip>` (e.g., `https://192.168.1.104`)
3. Click **Advanced** then **Proceed to site (unsafe)**
4. The app works normally, but the warning appears each new session

## Option B: Import Certificate via GUI (permanent, no warnings)

1. Copy the certificate file to the Windows machine:
   - Source: `deploy/certs/gacpa.crt` on the Mac
   - Transfer via USB drive, email attachment, or shared folder
2. On Windows, double-click `gacpa.crt`
3. Click **Install Certificate...**
4. Select **Local Machine** (requires admin) or **Current User**
5. Choose **Place all certificates in the following store**
6. Click **Browse** and select **Trusted Root Certification Authorities**
7. Click **Next**, then **Finish**
8. Restart the browser completely
9. Navigate to `https://<mac-ip>` — no more warning

## Option C: PowerShell (admin, one command)

Open PowerShell as Administrator and run:

```powershell
Import-Certificate -FilePath "C:\path\to\gacpa.crt" -CertStoreLocation Cert:\LocalMachine\Root
```

Replace `C:\path\to\gacpa.crt` with the actual path where you saved the
certificate file. Restart the browser after importing.

## Notes

- The certificate is valid for 10 years from generation date
- If the Mac's IP address changes, `deploy/setup.sh` will regenerate the
  certificate automatically. You will need to re-import the new cert on
  Windows machines.
- The certificate only works for the specific IP address embedded in it.
  Check the current IP by running `ipconfig getifaddr en0` on the Mac.
