#!/usr/bin/env python3
"""
Your Daily Phil -> WhatsApp post, delivered to Sruli's Slack DM.

Started weekday mornings by poll.yml (see dailyphil.yml). Waits for today's
Daily Phil to be published, then builds:

    Your Daily Phil: <edition title, verbatim>

    • <first story headline in the newsletter, verbatim>
    • <second>
    • <third>

    Read more: <plain eJP link to the edition>

Rules (from the eJP team): everything verbatim, copied character for
character. No emojis, hashtags or commentary. Bullet is U+2022.

Env:
  DM_SLACK_WEBHOOK  incoming webhook to Sruli's DM (unset = just print)
  DEADLINE_HOUR_ET       hour (ET) to give up waiting; default 15
"""

import datetime
import html
import json
import os
import re
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo

API = "https://ejewishphilanthropy.com/wp-json/wp/v2/posts"
NUM_STORIES = 3
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
ET = ZoneInfo("America/New_York")
WAIT_SECONDS = 300

WEBHOOK = os.environ.get("DM_SLACK_WEBHOOK", "").strip()
DEADLINE_HOUR_ET = int(os.environ.get("DEADLINE_HOUR_ET", "15"))


def get_json(url):
    url = f"{url}&_cb={int(time.time())}"  # dodge the edge cache
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def verbatim(fragment):
    """Text exactly as it reads in the newsletter: tags removed, entities
    decoded, nothing else changed (quotes, dashes, caps all kept)."""
    text = html.unescape(re.sub(r"<[^>]+>", "", fragment))
    return re.sub(r"\s+", " ", text).strip()


def todays_edition():
    today = datetime.datetime.now(ET).date().isoformat()
    posts = get_json(f"{API}?search=your%20daily%20phil&orderby=date&per_page=10"
                     "&_fields=date,link,title,content")
    for p in posts:
        slug = p["link"].rstrip("/").rsplit("/", 1)[-1]
        if slug.startswith("your-daily-phil-") and p["date"].startswith(today):
            return p
    return None


def build():
    edition = None
    while True:
        try:
            edition = todays_edition()
        except Exception as e:  # transient site hiccup: keep waiting
            print(f"lookup failed: {e}", file=sys.stderr)
        if edition:
            break
        if datetime.datetime.now(ET).hour >= DEADLINE_HOUR_ET:
            raise RuntimeError("today's Daily Phil never showed up on the site "
                               "(holiday, or it's very late)")
        print("Daily Phil not up yet, waiting...", file=sys.stderr)
        time.sleep(WAIT_SECONDS)

    title = verbatim(edition["title"]["rendered"])
    if not title.startswith("Your Daily Phil:"):
        title = f"Your Daily Phil: {title}"
    heads = re.findall(r'class="headline"[^>]*>\s*<h3[^>]*>(.*?)</h3>',
                       edition["content"]["rendered"], re.S)
    heads = [verbatim(h) for h in heads][:NUM_STORIES]
    if len(heads) < NUM_STORIES:
        raise RuntimeError(f"only found {len(heads)} stories in {edition['link']}")

    lines = [title, ""] + [f"• {h}" for h in heads]
    lines += ["", f"Read more: {edition['link']}"]
    return "\n".join(lines)


def slack(text):
    if not WEBHOOK:
        print(text)
        return
    req = urllib.request.Request(
        WEBHOOK,
        data=json.dumps({"text": text, "unfurl_links": False,
                         "unfurl_media": False}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=30).read()


def main():
    try:
        post = build()
    except Exception as e:
        slack(f":warning: Couldn't build today's Daily Phil WhatsApp post: {e}")
        raise
    if datetime.datetime.now(ET).hour >= 16:
        post = (":warning: Late: the morning trigger didn't fire, so this came from "
                "the backup schedule. Check the eJP watcher's cron-job.org pinger.\n\n"
                + post)
    slack(post)


if __name__ == "__main__":
    main()
