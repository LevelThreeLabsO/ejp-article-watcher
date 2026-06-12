# eJewishPhilanthropy article watcher

Posts every newly published eJewishPhilanthropy article to a Slack channel as a
link (which Slack unfurls into a preview), within a few minutes of publish.

Runs 24/7 as a GitHub Actions workflow — it does **not** depend on any personal
machine being on. It reads the public eJewishPhilanthropy WordPress REST API, so
no login or cookie is needed.

Sibling of the Jewish Insider and The Circuit watchers; this one is independent
(its own repo, pinger, Slack webhook, and state).

## How it works

- `.github/workflows/poll.yml` runs `poll.py`, triggered by an external
  cron-job.org pinger (via the `workflow_dispatch` API) every few minutes. A
  `*/15` GitHub `schedule` is a laggy fallback if the pinger stops.
- `poll.py` fetches the 20 most recent posts and Slacks any it hasn't seen.
- Seen post IDs are stored in `watcher_state.json`, committed back each run.
- The Slack webhook is the `SLACK_WEBHOOK_URL` repository secret.

## First run

On the first run (no `watcher_state.json` yet) it records current posts as a
baseline and posts a single "watcher is live" message — it does not backfill.

## Local test

```bash
pip install -r requirements.txt
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..." python poll.py
```
