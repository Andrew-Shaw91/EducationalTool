# Deploying CodeSense to an Ubuntu 24.04 VM

A step-by-step guide for putting the CodeSense prototype on a single cloud VM so that participants and your supervisor can use it from their own browsers. It assumes little Linux experience: every step gives the exact command and what you should see.

**What you will end up with**

```
Browser --> nginx (port 80) --> gunicorn (127.0.0.1:8000) --> Django --> SQLite file
              |
              +--> serves /static/ files directly
```

- **nginx** is the public front door. It serves CSS/JavaScript/fonts itself and passes everything else to gunicorn.
- **gunicorn** runs the Django application. **systemd** starts it at boot and restarts it if it crashes.
- **SQLite** stores the data in one file, kept outside the code folder.
- The firewall (**UFW**) allows only SSH and web traffic.

This is a setup for a research prototype: simple and reliable, not built for large scale. A checklist version for repeat deployments is in [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md).

---

## Before you start

You need:

- A VM running **Ubuntu 24.04 LTS** with a **public IP address** and SSH access (a user that can run `sudo`; on many providers this user is called `ubuntu`).
- Ports **80** (web) and **22** (SSH) open in your **cloud provider's own firewall / security group** as well as on the VM. Port 443 too if you will add HTTPS later. This is the most common reason a new site "does not load from outside".

How to read this guide:

- `YOUR_USER` = your login name on the VM. `YOUR_VM_IP` = the VM's public IP address. Replace both everywhere.
- Commands marked **On your PC** run in PowerShell on your Windows machine. Commands marked **On the VM** run in an SSH session.
- Copy commands one block at a time. If a command prints an error, stop and read [Troubleshooting](#troubleshooting).

### Folder layout used throughout

| Path on the VM | What it is |
|----------------|------------|
| `/srv/codesense/app` | The project code, `.env` settings file, `logs/`, `staticfiles/` |
| `/srv/codesense/venv` | Python virtual environment (the installed packages) |
| `/srv/codesense/data` | The SQLite database (`db.sqlite3`) and its backups |

The application runs as a dedicated, login-less user called `codesense`, so a fault in the web app cannot touch the rest of the server.

---

## Step 0. Connect to the VM and install the system packages

**On your PC:**

```powershell
ssh YOUR_USER@YOUR_VM_IP
```

(The first time, type `yes` to accept the server's fingerprint.)

**On the VM:**

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip nginx sqlite3 ufw
python3 --version
```

You should see `Python 3.12.x`, which is what Ubuntu 24.04 ships and what Django 5.2 supports.

---

## Step 1. Copy the project to the VM

### 1a. Create the service user and folders (On the VM)

```bash
sudo adduser --system --group --home /srv/codesense --shell /usr/sbin/nologin codesense
sudo mkdir -p /srv/codesense/app /srv/codesense/data/backups
sudo chown -R codesense:codesense /srv/codesense
sudo chmod 755 /srv/codesense
sudo chmod 750 /srv/codesense/data
```

### 1b. Pack the project (On your PC)

This bundles your project into one file, leaving out things that must not be copied (your local virtual environment, local database, local logs and secrets).

```powershell
cd "C:\Users\Bawke\OneDrive\Desktop\EducationalTool"
tar -czf "$env:TEMP\codesense.tar.gz" --exclude=.venv --exclude=__pycache__ --exclude=db.sqlite3 --exclude=staticfiles --exclude=logs --exclude=.env --exclude=.git .
```

### 1c. Upload it (On your PC)

```powershell
scp "$env:TEMP\codesense.tar.gz" YOUR_USER@YOUR_VM_IP:/tmp/
```

### 1d. Unpack it (On the VM)

```bash
sudo tar -xzf /tmp/codesense.tar.gz --no-same-owner -C /srv/codesense/app
sudo chown -R codesense:codesense /srv/codesense/app
sudo sed -i 's/\r$//' /srv/codesense/app/deploy/* /srv/codesense/app/.env.example
sudo chmod +x /srv/codesense/app/deploy/backup_db.sh
rm /tmp/codesense.tar.gz
ls /srv/codesense/app
```

You should see `manage.py`, `codesense`, `practice`, `research`, `deploy`, `DEPLOYMENT.md` and more. (The `sed` line removes any Windows line endings from the server files, which would stop the backup script and the service file working. It is harmless if there are none.)

**From here on, run commands from the project folder:**

```bash
cd /srv/codesense/app
```

Every command below that starts `sudo -u codesense` runs *as the service user*, so files it creates have the right owner.

---

## Step 2. Create a Python virtual environment

A virtual environment is a private folder of Python packages for this one project.

```bash
sudo -u codesense python3 -m venv /srv/codesense/venv
```

Nothing is printed when it works. You will not need to "activate" it by hand in this guide: the commands below call the programs inside it directly (for example `/srv/codesense/venv/bin/python`), and the systemd service does the same, which has the same effect as activating it.

---

## Step 3. Install the requirements

```bash
sudo -u codesense /srv/codesense/venv/bin/pip install --upgrade pip
sudo -u codesense /srv/codesense/venv/bin/pip install -r requirements.txt
```

The last lines should say `Successfully installed ... Django-5.2.x ... gunicorn-...`.

### 3b. Create the settings file (`.env`)

Settings and secrets live in a file called `.env`, which is never copied between machines and never shared.

```bash
sudo -u codesense cp .env.example .env
sudo -u codesense chmod 600 .env
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

The last command prints a long random string. Select it and copy it (right-click usually copies in an SSH window), then open the file:

```bash
sudo -u codesense nano .env
```

Change these lines (leave the others alone):

```ini
DEBUG=False
SECRET_KEY=PASTE_THE_LONG_RANDOM_STRING_HERE
ALLOWED_HOSTS=YOUR_VM_IP,localhost,127.0.0.1
DATABASE_PATH=/srv/codesense/data/db.sqlite3
USE_HTTPS=False
CODESENSE_LLM_API_KEY=
```

- **No spaces** around `=`, and no quotes needed.
- `ALLOWED_HOSTS` is the list of addresses people will type into the browser. Add your domain later (see [Adding a domain name and HTTPS](#adding-a-domain-name-and-https)).
- Keep `USE_HTTPS=False` while you are using `http://YOUR_VM_IP`. Turning it on without HTTPS makes forms stop working.
- Leave `CODESENSE_LLM_API_KEY` **empty**. The app works fully without it, and no real LLM adapter has been written yet, so a key would have nothing to call.

Save with **Ctrl+O**, **Enter**, then exit with **Ctrl+X**.

Check the settings load:

```bash
sudo -u codesense /srv/codesense/venv/bin/python manage.py check --deploy
```

You should see `System check identified ... issues`. Warnings `security.W004`, `W008`, `W012` and `W016` are **expected** until you add HTTPS (they are about HTTPS-only protections). Any message mentioning `SECRET_KEY` or `DEBUG` means `.env` is wrong. An `ImproperlyConfigured` error means the same: recheck the file.

---

## Step 4. Run the migrations (and load the activities)

```bash
sudo -u codesense /srv/codesense/venv/bin/python manage.py migrate
sudo -u codesense /srv/codesense/venv/bin/python manage.py seed_activities
```

`migrate` creates the database tables (you will see a list of `Applying ... OK`). `seed_activities` loads the teaching content. **Do not skip it: without it the site has no activities.** It should print `Seeded 16 question types, 6 topics, 48 new activities, 0 updated activities.`

Recommended: run the project's test suite on the VM to confirm everything works on this machine.

```bash
sudo -u codesense env USE_HTTPS=False /srv/codesense/venv/bin/python manage.py test
```

The last lines should be `Ran ... tests` and `OK`.

Optional: create an admin login to view responses in the browser at `/admin/` (it is read-only for research data). Choose a strong password.

```bash
sudo -u codesense /srv/codesense/venv/bin/python manage.py createsuperuser
```

---

## Step 5. Collect the static files

```bash
sudo -u codesense /srv/codesense/venv/bin/python manage.py collectstatic --noinput
```

This copies the CSS, JavaScript and fonts into `/srv/codesense/app/staticfiles/`, which nginx serves. You should see `... static files copied to '/srv/codesense/app/staticfiles'`.

---

## Step 6. Start gunicorn (a first test)

```bash
sudo -u codesense /srv/codesense/venv/bin/gunicorn --config deploy/gunicorn.conf.py codesense.wsgi:application
```

You should see lines such as `Listening at: http://127.0.0.1:8000` and `Booting worker with pid ...`. This window is now busy running the server.

Open a **second SSH window** (repeat the `ssh` command from Step 0) and run:

```bash
curl -sI http://127.0.0.1:8000/ | head -n 1
```

`HTTP/1.1 200 OK` means the application works. Go back to the first window and press **Ctrl+C** to stop gunicorn; systemd will run it properly in Step 8.

---

## Step 7. Install and configure nginx

nginx is already installed (Step 0). Install this project's configuration:

```bash
cd /srv/codesense/app
sudo cp deploy/nginx-codesense.conf /etc/nginx/sites-available/codesense
sudo ln -sf /etc/nginx/sites-available/codesense /etc/nginx/sites-enabled/codesense
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
```

`nginx -t` must print `syntax is ok` and `test is successful`. Then:

```bash
sudo systemctl reload nginx
```

What this configuration does: serves `/static/` straight from `staticfiles/`; passes everything else to gunicorn on `127.0.0.1:8000`; sets security headers (no sniffing, no framing, strict content policy); hides the nginx version; and limits each visitor to about 20 requests per second. It answers on the bare IP address now and works unchanged once you add a domain.

Until the service in Step 8 is running, the site shows `502 Bad Gateway`. That is expected.

---

## Step 8. Create the systemd service

```bash
sudo cp deploy/codesense.service /etc/systemd/system/codesense.service
sudo systemctl daemon-reload
```

The service file (`deploy/codesense.service`) runs gunicorn from the virtual environment as the `codesense` user, restarts it automatically if it fails, and reads settings from `.env`.

---

## Step 9. Enable automatic startup

```bash
sudo systemctl enable --now codesense
sudo systemctl status codesense
```

`enable` makes it start at every boot; `--now` also starts it immediately. `status` should show **`active (running)`** in green (press **q** to leave). nginx also starts at boot on its own; confirm with `systemctl is-enabled nginx`, which should print `enabled`.

Useful commands:

| Command | What it does |
|---------|--------------|
| `sudo systemctl restart codesense` | Restart the app (after changing `.env` or code) |
| `sudo systemctl reload codesense` | Gracefully reload workers |
| `sudo systemctl stop codesense` | Stop the app |
| `sudo systemctl status codesense` | Is it running? |

---

## Step 10. Configure the UFW firewall

**Allow SSH first**, or you will lock yourself out.

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status verbose
```

Answer `y` when asked. `Nginx Full` opens ports 80 and 443. The status should list `OpenSSH` and `Nginx Full` as `ALLOW`, with default incoming `deny`. Port 8000 stays closed: only nginx on the same machine can reach gunicorn.

Now try it from your PC. Open **http://YOUR_VM_IP/** in a browser: you should see the CodeSense home page, correctly styled.

If it loads on the VM but not from outside, check your **cloud provider's firewall / security group** allows ports 80 and 22. **Oracle Cloud needs two extra things, described next.**

### Oracle Cloud (OCI) notes

Oracle blocks web traffic in **two** places that are not part of Ubuntu itself. You must open both, or the site will time out from outside even though everything on the VM is fine.

**1. Open the ports in the Oracle console (once).** In the Oracle Cloud web console: *Networking → Virtual cloud networks →* your VCN *→ Subnets →* your subnet *→ Security Lists →* the default security list *→ Add Ingress Rules*. Add one rule for each of port 80 and port 443:

| Field | Value |
|-------|-------|
| Source type | CIDR |
| Source CIDR | `0.0.0.0/0` |
| IP protocol | TCP |
| Destination port range | `80` (then repeat with `443`) |

(Port 22 for SSH is already there. If your VM uses a Network Security Group instead of the security list, add the same rules there.)

**2. Open the ports in the firewall rules inside Oracle's Ubuntu image (On the VM).** Oracle's images ship with iptables rules that reject everything except SSH, in addition to UFW. Insert accept rules for web traffic and save them so they survive a reboot:

```bash
sudo iptables -I INPUT 1 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 1 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

If `netfilter-persistent` is not found, run `sudo apt install -y iptables-persistent` (answer *Yes* to saving current rules) and repeat the last command.

Do this together with the UFW commands above. Then **reboot once and test from your PC** (`sudo reboot`, wait a minute, open `http://YOUR_VM_IP/`) to confirm the rules survive a restart.

Two more Oracle details: your VM sees a private address internally, but `ALLOWED_HOSTS` must contain the **public** IP, because that is what visitors type; and on Oracle's Ampere (ARM) shapes everything in this guide works unchanged.

---

## Step 11. Check the logs

| What | Command |
|------|---------|
| Application log (Django errors and warnings) | `sudo tail -n 50 /srv/codesense/app/logs/codesense.log` |
| Follow it live (Ctrl+C to stop) | `sudo tail -f /srv/codesense/app/logs/codesense.log` |
| Service output (gunicorn, startup errors) | `sudo journalctl -u codesense -n 50 --no-pager` |
| Follow it live | `sudo journalctl -u codesense -f` |
| nginx errors | `sudo tail -n 50 /var/log/nginx/codesense.error.log` |
| Who visited (nginx) | `sudo tail -n 50 /var/log/nginx/codesense.access.log` |

Set up automatic log rotation once, so the log cannot fill the disk:

```bash
sudo cp /srv/codesense/app/deploy/codesense.logrotate /etc/logrotate.d/codesense
sudo logrotate --debug /etc/logrotate.d/codesense
```

(Rotation happens weekly and keeps 8 weeks.) The same service output also goes to the system journal, which Ubuntu limits automatically.

---

## Step 12. Updating the application

When you change the code on your PC:

**On your PC:** pack and upload as in Steps 1b and 1c. Use a new file name each time so you keep old versions for rollback, for example:

```powershell
cd "C:\Users\Bawke\OneDrive\Desktop\EducationalTool"
tar -czf "$env:TEMP\codesense-update.tar.gz" --exclude=.venv --exclude=__pycache__ --exclude=db.sqlite3 --exclude=staticfiles --exclude=logs --exclude=.env --exclude=.git .
scp "$env:TEMP\codesense-update.tar.gz" YOUR_USER@YOUR_VM_IP:/tmp/
```

**On the VM:**

```bash
cd /srv/codesense/app
sudo -u codesense ./deploy/backup_db.sh
sudo tar -xzf /tmp/codesense-update.tar.gz --no-same-owner -C /srv/codesense/app
sudo chown -R codesense:codesense /srv/codesense/app
sudo sed -i 's/\r$//' deploy/* .env.example && sudo chmod +x deploy/backup_db.sh
sudo -u codesense /srv/codesense/venv/bin/pip install -r requirements.txt
sudo -u codesense /srv/codesense/venv/bin/python manage.py migrate
sudo -u codesense /srv/codesense/venv/bin/python manage.py seed_activities
sudo -u codesense /srv/codesense/venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart codesense
sudo systemctl status codesense
mv /tmp/codesense-update.tar.gz ~/codesense-$(date +%Y%m%d).tar.gz
```

Your `.env`, database, logs and virtual environment are untouched because they were left out of the archive or live outside the code folder.

> **Once real participants have used the site, treat the activities as frozen.** `seed_activities` updates content in place. Editing an activity's wording is safe, but **changing a title, or inserting a multiple-choice item before existing ones, can change which option a stored answer refers to, or create a duplicate activity** (see "Adding or editing activities" in the README). If you must change content mid-study, back up first and note the change date for your analysis.

**Rolling back:** if an update breaks the site, unpack the previous archive the same way (`sudo tar -xzf ~/codesense-DATE.tar.gz --no-same-owner -C /srv/codesense/app`), run `chown`, `collectstatic` and `restart`. If the database is damaged, see [Backups](#backups).

---

# Extras

## Giving your supervisor access

The site is public, so send your supervisor the address `http://YOUR_VM_IP/` (or your domain). They need no account. To let them see recorded responses, create an admin login for them with `createsuperuser` (Step 4) and give them `/admin/`; research data is read-only there.

To keep the site **private while you finish preparing** (browsers ask for a name and password), add basic authentication:

```bash
sudo apt install -y apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd supervisor
```

Then edit `/etc/nginx/sites-available/codesense` (`sudo nano ...`) and add these two lines just below `server_name _;`:

```nginx
    auth_basic "CodeSense prototype";
    auth_basic_user_file /etc/nginx/.htpasswd;
```

Run `sudo nginx -t && sudo systemctl reload nginx`. Remove the two lines to open the site to everyone.

Because participants' answers are stored on this server, make sure the study has ethical approval and that participants are informed, as set out in `design_notes.md` (section 4). The site footer already tells participants what is recorded.

## Exporting research data

```bash
cd /srv/codesense/app
sudo -u codesense /srv/codesense/venv/bin/python manage.py export_research_data --output /tmp/attempts.csv
```

**On your PC:**

```powershell
scp YOUR_USER@YOUR_VM_IP:/tmp/attempts.csv .
```

Then delete the copy on the VM: `rm /tmp/attempts.csv`.

## Adding a domain name and HTTPS

HTTPS needs a domain name (certificates are issued for names, not bare IP addresses).

1. At your domain registrar, create an **A record** pointing the domain (and `www`, if wanted) to `YOUR_VM_IP`. Wait for it to take effect (often minutes; up to a few hours).
2. On the VM, edit the nginx site: `sudo nano /etc/nginx/sites-available/codesense` and change `server_name _;` to `server_name example.org www.example.org;`. Then `sudo nginx -t && sudo systemctl reload nginx`.
3. Get a free certificate (Let's Encrypt) and let it update nginx:

   ```bash
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d example.org -d www.example.org
   ```

   Choose the option to redirect HTTP to HTTPS. Renewal is automatic (`sudo certbot renew --dry-run` tests it).
4. Edit `.env` (`sudo -u codesense nano /srv/codesense/app/.env`):

   ```ini
   ALLOWED_HOSTS=example.org,www.example.org,YOUR_VM_IP,localhost,127.0.0.1
   CSRF_TRUSTED_ORIGINS=https://example.org,https://www.example.org
   USE_HTTPS=True
   ```

5. `sudo systemctl restart codesense`, then open `https://example.org/`.
6. Optional once everything works: add `SECURE_HSTS_SECONDS=3600` to `.env` and restart. It tells browsers to insist on HTTPS. Raise it later (for example to `31536000`) only when you are sure you will keep HTTPS.

With `USE_HTTPS=True`, secure cookies and an HTTP-to-HTTPS redirect are on, so `curl http://127.0.0.1:8000/` on the VM will answer with a redirect. That is normal.

## Backups

The database holds your research data. `deploy/backup_db.sh` makes a safe copy while the site is running and keeps the last 14.

Run it once by hand:

```bash
sudo -u codesense /srv/codesense/app/deploy/backup_db.sh
ls -lh /srv/codesense/data/backups
```

Run it automatically every night at 02:30:

```bash
echo '30 2 * * * codesense /srv/codesense/app/deploy/backup_db.sh >> /srv/codesense/data/backup.log 2>&1' | sudo tee /etc/cron.d/codesense-backup
```

Backups on the same VM do not protect you if the VM is lost. Occasionally copy them to your PC:

```powershell
scp -r YOUR_USER@YOUR_VM_IP:/srv/codesense/data/backups .
```

(You may need `sudo chmod -R a+rX /srv/codesense/data` for your login user to read them, or use the export command above.)

**Restoring** a backup (stops the site briefly):

```bash
sudo systemctl stop codesense
gunzip -c /srv/codesense/data/backups/db-YYYYMMDD-HHMMSS.sqlite3.gz | sudo -u codesense tee /srv/codesense/data/db.sqlite3 > /dev/null
sudo rm -f /srv/codesense/data/db.sqlite3-wal /srv/codesense/data/db.sqlite3-shm
sudo systemctl start codesense
```

Never copy `db.sqlite3` with plain `cp` while the site is running: in this setup SQLite also keeps recent changes in side files (`-wal`, `-shm`), so a plain copy can be incomplete.

## Troubleshooting

| What you see | Likely cause and fix |
|--------------|----------------------|
| **502 Bad Gateway** | gunicorn is not running. `sudo systemctl status codesense`, then `sudo journalctl -u codesense -n 50 --no-pager` for the reason. |
| **400 Bad Request** | The address you typed is not in `ALLOWED_HOSTS` in `.env`. Add it, then `sudo systemctl restart codesense`. |
| **403 CSRF verification failed** when submitting an answer | With a domain and HTTPS: `CSRF_TRUSTED_ORIGINS` and `USE_HTTPS` must be set as in the HTTPS section. Over plain `http://IP`: `USE_HTTPS` must be `False`. Clear the browser's cookies for the site and retry. |
| Page loads with no styling | Run `collectstatic` (Step 5). Check nginx can read the files: `sudo -u www-data ls /srv/codesense/app/staticfiles/css`. |
| **429 Too Many Requests** | The rate limit in the nginx file was hit (about 20 requests/second per IP). Raise `rate=` and `burst=` in `/etc/nginx/sites-available/codesense`. |
| Service fails and the journal says **ImproperlyConfigured ... SECRET_KEY** | `.env` still has the placeholder, or `DEBUG=False` with no key. Fix `.env`, restart. |
| **attempt to write a readonly database** / **unable to open database file** | The `codesense` user cannot write the data folder. `sudo chown -R codesense:codesense /srv/codesense/data`. Check `DATABASE_PATH` in `.env`. |
| **database is locked** | Rare with this setup (it waits up to 20 s). If frequent, set `GUNICORN_WORKERS=2` for the service (`sudo systemctl edit codesense`, add `[Service]` and `Environment=GUNICORN_WORKERS=2`). |
| The site is empty (no topics or activities) | `seed_activities` was not run (Step 4). |
| Changed `.env` but nothing changed | `sudo systemctl restart codesense`. |
| Cannot reach the site from outside, but `curl` on the VM works | Cloud provider firewall / security group, or `sudo ufw status`. |
| Locked out of SSH after enabling UFW | Use your provider's web console, run `sudo ufw allow OpenSSH`. |
