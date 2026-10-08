# Run the actual website on Windows

You need Docker Desktop running with **Linux containers**. Python, Node.js, PostgreSQL, Redis, and an SMTP subscription are not needed on Windows: Docker supplies the application services.

## First start

1. Download the repository using GitHub's **Code -> Download ZIP**, or clone it:
   ```powershell
   git clone https://github.com/Rx4eddy/n2ncp.git
   ```
2. If using a ZIP, right-click the downloaded ZIP, select **Properties**, check **Unblock** if Windows shows that option, and apply. This marks your deliberately downloaded copy as trusted; do not change your machine-wide PowerShell execution policy. Then **Extract All** into a normal local folder, for example `C:\Projects\n2ncp`. Do not run from inside the ZIP or a OneDrive-synced folder.
3. Double-click **start-windows.cmd** in the extracted repository folder. The first run downloads dependencies and builds images, which can take several minutes. Keep Docker Desktop open.
4. The launcher generates `.env` secrets if that file is missing, migrates and seeds PostgreSQL, starts the website and background services, checks readiness, and opens your browser.
5. The site runs at `http://localhost:8000`. Click **Create account**, enter your email and a password, then open the verification message at `http://localhost:8025`. Click the message's verification link and sign in.

The inbox is a local email viewer (Mailpit). Messages stay on your computer; they are not sent to the entered email's external inbox. Check it for password-reset and reminder emails too. Allow up to 30 seconds for queued messages.

There is no default login or shared administrator password. Your account, notes, solves, and progress are stored in your local PostgreSQL Docker volume. The seed contains 267 curated problems and 32 practice modules; the calendar populates after its first successful background refresh.

## Returning later

Keep Docker Desktop running and double-click `start-windows.cmd` again. Existing secrets and data are preserved. Close the launcher window after startup if you want; the site stays running in Docker Desktop.

Double-click `stop-windows.cmd` to stop the services without deleting your data. To update a Git checkout, stop the app, run `git pull --ff-only`, then start again. If you downloaded a ZIP, preserve the existing `.env` and folder rather than replacing an installed copy blindly. Back up first before applying an update with database migrations.

PowerShell alternatives, from the repository folder:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\Start-Windows.ps1
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\Start-Windows.ps1 -NoBrowser
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\Start-Windows.ps1 -Action Stop
```

The execution-policy option applies to that process only. If your organization enforces a policy that blocks scripts, use its approved route or the manual Docker instructions in the README; do not bypass organizational policy.

## Troubleshooting

### Docker Desktop or WSL is not ready

Open Docker Desktop and resolve its displayed WSL/virtualization requirement. Use Windows' supported WSL installation/update workflow if requested, and restart Windows when required. The launcher waits up to two minutes for an installed Docker Desktop to become ready. Select Linux containers, not Windows containers.

### A port is already allocated

The app uses local ports **8000** (website) and **8025** (email viewer). Identify the other application and stop it if appropriate; the launcher never kills unrelated processes.

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8000,8025 -ErrorAction SilentlyContinue |
    Select-Object LocalAddress,LocalPort,OwningProcess
```

### The browser cannot connect or an email does not appear

Run these commands from the repository folder:

```powershell
docker compose ps
docker compose logs --tail=80 init web worker beat mailpit
Invoke-RestMethod http://localhost:8000/health/
docker compose exec worker celery -A config inspect ping --timeout=5
```

Expected: web/db/redis/mailpit/worker/beat running, health status `ok`, and worker `pong`. The `assets` and `init` services normally show **Exited (0)** after successful preparation. Check the local inbox, not your Gmail/Outlook inbox. A successful web health check alone does not establish worker readiness; the launcher checks both.

### Existing `.env` contains placeholders or production settings

The launcher deliberately preserves an existing `.env`. On a **brand-new installation that has never initialized a database**, remove only the unused placeholder `.env` and start again to generate real local secrets. If you have existing data, edit the settings carefully and keep the database password consistent with that database. Changing `POSTGRES_PASSWORD` in a file does not change an already initialized PostgreSQL password.

For an existing local instance, `DEBUG` must be `1`, `SITE_URL` must be `http://localhost:8000` (or `http://127.0.0.1:8000`), and `ALLOWED_HOSTS` must include both `localhost` and `127.0.0.1`. The generated database password uses URL-safe hexadecimal characters. Use a separate checkout/folder for production settings.

**Do not delete volumes or use `docker compose down -v` to fix a startup problem.** That removes your accounts and journal. Follow the backup/restore guide before intentional data removal.

### Network, antivirus, or corporate proxy blocks downloads

Allow Docker Desktop's documented network access through your approved settings. Configure your trusted corporate CA/proxy if needed. Do not disable TLS verification or antivirus globally. A registry/network error is different from an application error; keep the failure message when requesting help, but never share `.env`, passwords, tokens, or a database dump.

### Only one contest platform fails

Check the calendar's sync status. Public platforms can rate-limit or block requests temporarily; other features remain available. Codeforces and AtCoder support account ownership verification. CodeChef/CSES support manual logging, and LeetCode remains static-only.
