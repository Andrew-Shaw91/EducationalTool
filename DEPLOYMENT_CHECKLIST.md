# CodeSense deployment checklist (Ubuntu 24.04)

Follow this when moving the application to a new server. Every step is explained, with the exact commands, in [DEPLOYMENT.md](DEPLOYMENT.md). Replace `YOUR_USER` and `YOUR_VM_IP`.

Tick each box as you go. Do not move to the next section until the "Check" line passes.

## A. Before you touch the server

- [ ] VM is **Ubuntu 24.04 LTS**, has a public IP, and you can `ssh YOUR_USER@YOUR_VM_IP`.
- [ ] Cloud provider firewall / security group allows **22** (SSH) and **80** (web), plus **443** if HTTPS is planned.
- [ ] Tests pass on your PC: `python manage.py test` ends with `OK`.
- [ ] Study ethics approval is in place, because the server stores participant answers (`design_notes.md`, section 4).
- [ ] You decided whether the site starts private (basic auth) or public.

## B. Prepare the server

- [ ] `sudo apt update && sudo apt upgrade -y`
- [ ] `sudo apt install -y python3-venv python3-pip nginx sqlite3 ufw`
- [ ] **Check:** `python3 --version` shows 3.12.x.
- [ ] Service user and folders created (`adduser --system ... codesense`; `/srv/codesense/{app,data/backups}`; owner `codesense`).

## C. Install the application

- [ ] Project packed on your PC with `tar` (excluding `.venv`, `db.sqlite3`, `logs`, `staticfiles`, `.env`, `.git`) and uploaded with `scp`.
- [ ] Unpacked into `/srv/codesense/app`; `chown -R codesense:codesense /srv/codesense/app`.
- [ ] Windows line endings removed from the server files (`sed -i 's/\r$//' deploy/* .env.example`); backup script is executable.
- [ ] Virtual environment created: `sudo -u codesense python3 -m venv /srv/codesense/venv`.
- [ ] Requirements installed: `pip install -r requirements.txt` finished with `Successfully installed`.
- [ ] `.env` created from `.env.example`, permissions `600`, owner `codesense`.
- [ ] In `.env`: `DEBUG=False`.
- [ ] In `.env`: `SECRET_KEY` is a new random value (not the placeholder, not reused from another machine).
- [ ] In `.env`: `ALLOWED_HOSTS` contains the server IP (and domain, if any), `localhost`, `127.0.0.1`.
- [ ] In `.env`: `DATABASE_PATH=/srv/codesense/data/db.sqlite3`.
- [ ] In `.env`: `USE_HTTPS=False` for plain-IP access (`True` only once HTTPS works).
- [ ] In `.env`: `CODESENSE_LLM_API_KEY` is **empty** (no LLM adapter exists yet).
- [ ] **Check:** `manage.py check --deploy` shows no `SECRET_KEY` or `DEBUG` warnings (HTTPS warnings are expected without HTTPS).
- [ ] `manage.py migrate` finished without errors.
- [ ] `manage.py seed_activities` printed `Seeded 16 question types, 6 topics, 48 ...`.
- [ ] `sudo -u codesense env USE_HTTPS=False .../python manage.py test` ends with `OK`.
- [ ] `manage.py collectstatic --noinput` copied the static files.
- [ ] **Check:** gunicorn started by hand answers `curl -sI http://127.0.0.1:8000/` with `200 OK` (then stopped with Ctrl+C).

## D. Web server and service

- [ ] nginx site installed to `sites-available/codesense`, linked in `sites-enabled`, default site removed.
- [ ] **Check:** `sudo nginx -t` says `test is successful`; nginx reloaded.
- [ ] `codesense.service` copied to `/etc/systemd/system/`; `daemon-reload` run.
- [ ] `sudo systemctl enable --now codesense`
- [ ] **Check:** `systemctl status codesense` shows `active (running)`; `systemctl is-enabled codesense nginx` shows `enabled` twice.
- [ ] UFW: `allow OpenSSH` **first**, then `allow 'Nginx Full'`, then `ufw enable`.
- [ ] **Check:** `sudo ufw status` lists OpenSSH and Nginx Full; port 8000 is not listed.
- [ ] Oracle Cloud only: ingress rules for TCP 80 and 443 added in the console (security list or NSG), **and** iptables accept rules added inside the VM and saved with `sudo netfilter-persistent save` (DEPLOYMENT.md, "Oracle Cloud (OCI) notes").
- [ ] **Check from another computer:** `http://YOUR_VM_IP/` shows the home page **with styling**; open an activity, submit an answer, see the feedback page.

## E. Operations

- [ ] Logs readable: `sudo tail /srv/codesense/app/logs/codesense.log` and `sudo journalctl -u codesense -n 20`.
- [ ] Log rotation installed (`/etc/logrotate.d/codesense`); `sudo logrotate --debug ...` shows no errors.
- [ ] Backup script runs by hand and creates a file in `/srv/codesense/data/backups`.
- [ ] Nightly backup cron installed (`/etc/cron.d/codesense-backup`).
- [ ] Reboot test: `sudo reboot`, wait a minute, reload the site. It comes back without you doing anything.
- [ ] Submitted one test answer, then confirmed it appears with `export_research_data` (or in `/admin/`), and deleted test data if it should not be in the study.
- [ ] Supervisor given the URL (and the basic-auth password or admin login, if used).

## F. Later: domain name and HTTPS

- [ ] DNS A record points to the server IP.
- [ ] nginx `server_name` changed from `_` to the domain; `nginx -t` and reload.
- [ ] `sudo certbot --nginx -d example.org -d www.example.org` succeeded; HTTP redirects to HTTPS.
- [ ] `.env`: domain added to `ALLOWED_HOSTS`; `CSRF_TRUSTED_ORIGINS=https://example.org,...`; `USE_HTTPS=True`.
- [ ] `sudo systemctl restart codesense`; submit an answer over HTTPS to prove forms still work.
- [ ] `sudo certbot renew --dry-run` succeeds.
- [ ] Optional: `SECURE_HSTS_SECONDS=3600` once HTTPS is stable.

## G. Before each update

- [ ] Backup taken (`sudo -u codesense ./deploy/backup_db.sh`).
- [ ] Previous archive kept for rollback.
- [ ] After updating: `pip install -r requirements.txt`, `migrate`, `seed_activities`, `collectstatic --noinput`, `systemctl restart codesense`, status is `active (running)`.
- [ ] If participants have already answered: activity titles unchanged and no multiple-choice item inserted before existing ones (see DEPLOYMENT.md, Step 12).
