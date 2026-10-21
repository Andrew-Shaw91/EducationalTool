# CodeSense

Research prototype for a Computing Science dissertation on introductory programming education in a generative-AI-rich environment.

This is **not** a general coding-practice site and **not** a ChatGPT tutorial. Students practise reading, tracing, debugging, evaluating AI-like suggestions, improving weak generated code, and stating requirements. AI is behind abstraction layers that currently return mocked, activity-aware scaffolding. It does not complete the learner's activity.

See [design_notes.md](design_notes.md) for the design rationale, assessment approach, ethics and future work.

## Run locally (works fully offline)

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_activities
python manage.py runserver
```

Open http://127.0.0.1:8000/. Bootstrap, fonts and CSS are served from `static/`; no internet connection is needed. Re-run `seed_activities` after changing activity content. Run the tests with `python manage.py test`.

## Project layout

| Path | Purpose |
|------|---------|
| `practice/` | **Activity data**: topics, question types, activities, evaluation logic, views |
| `practice/feedback/` | Pluggable free-text assessment (`FeedbackService`, `KeywordFeedbackService`, `AIEnhancedFeedbackService`) |
| `practice/ai/` | AI scaffolding layer (hints, explanations, follow-ups); mocked |
| `research/` | **Evaluation data**: `Participant`, `Attempt`, privacy switches, CSV export |
| `static/` | Vendored Bootstrap, fonts and project CSS |

## Adding or editing activities

Activities live in `practice/management/commands/seed_activities.py`; re-run `python manage.py seed_activities` after editing. Every topic should keep at least one activity at each Bloom level (tests enforce this). Rules to keep content trustworthy:

- **Append** new multiple-choice items to the *end* of `ACTIVITIES`. The loader spreads the correct answer evenly across positions by order, and inserting mid-list would shift earlier items.
- Write the correct option anywhere; the loader repositions it. Don't refer to options by letter in explanations.
- If an explanation claims what code outputs, add or update the matching case in `practice/test_content_claims.py`, which runs the code.
- Free-text items need `expected_concepts` (name, description, keywords).
- Every activity needs a `block_level` (`BlockLevel.ATOMS`, `BLOCKS`, `RELATIONS` or `MACRO`); the loader refuses an untagged one. The assignment rules are in `design_notes.md` (section 0a), and tests check them.

## Configuration

All options are in `codesense/settings.py` and can be overridden with environment variables, or with a `.env` file next to `manage.py` (copy `.env.example`; real environment variables win). With nothing set you get a working local development setup.

| Setting | Env var | Default | Effect |
|---------|---------|---------|--------|
| `DEBUG` | `DEBUG` | on | Set `False` on a server; the app then refuses to start without a real `SECRET_KEY` |
| `SECRET_KEY` | `SECRET_KEY` | development-only key | Required when `DEBUG` is off |
| `ALLOWED_HOSTS` | `ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated hosts/IPs the site may be served under |
| `CSRF_TRUSTED_ORIGINS` | `CSRF_TRUSTED_ORIGINS` | none | Full origins (`https://example.org`), needed with a domain and HTTPS |
| database file | `DATABASE_PATH` | `db.sqlite3` in the project | Lets a server keep the database outside the code folder |
| secure cookies, HTTPS redirect | `USE_HTTPS` | off | Turn on only once the site is served over HTTPS |
| `SECURE_HSTS_SECONDS` | `SECURE_HSTS_SECONDS` | `0` | Optional HSTS lifetime, used only with `USE_HTTPS` |
| log level | `LOG_LEVEL` | `DEBUG` (dev) / `INFO` | Logs go to the console and `logs/codesense.log` |
| `FEEDBACK_SERVICE` | `CODESENSE_FEEDBACK_SERVICE` | `keyword` | `keyword` or `ai` |
| `LLM_API_KEY` | `CODESENSE_LLM_API_KEY` | empty | With `ai` and no key, a labelled mock reply is used |
| `RESEARCH["ANALYTICS_ENABLED"]` | `CODESENSE_ANALYTICS` | on | Off = nothing is recorded at all |
| `RESEARCH["STORE_RESPONSE_TEXT"]` | `CODESENSE_STORE_RESPONSE_TEXT` | on | Off = answers' text is not stored |
| `RESEARCH["STORE_HINT_USAGE"]` | `CODESENSE_STORE_HINT_USAGE` | on | Off = hint counts are not stored |
| `RESEARCH["STORE_TIMESTAMPS"]` | `CODESENSE_STORE_TIMESTAMPS` | on | Off = no timestamps are stored |

Example: `CODESENSE_ANALYTICS=0 python manage.py runserver` collects no data.

## Research data

Participants are random codes such as `P-3F9A12C4`; no names, accounts, IP addresses or session keys are stored. Every field is documented in `research/models.py`.

```bash
python manage.py export_research_data --output attempts.csv
```

Evaluation data is also viewable (read-only) in the admin: `python manage.py createsuperuser`, then `/admin/`.

## Deploying beyond `runserver`

See [DEPLOYMENT.md](DEPLOYMENT.md) for a step-by-step guide to an Ubuntu 24.04 VM (nginx, gunicorn, systemd, UFW, backups) and [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) for a repeatable checklist. Ready-to-use configuration is in `deploy/` (`gunicorn.conf.py`, `codesense.service`, `nginx-codesense.conf`, `codesense.logrotate`, `backup_db.sh`). In short: set the variables above, run `migrate`, `seed_activities` and `collectstatic`, then run gunicorn behind nginx.
