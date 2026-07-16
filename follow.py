import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("❌ GITHUB_TOKEN not set")
    sys.exit(1)

USERNAME = os.environ.get("BOT_USERNAME", "")
FOLLOW_FILE = "follow.txt"
TARGET_USER = "torvalds"
MAX_FOLLOW = 600


def github_request(method, url, data=None):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-follow-bot",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    if data is not None:
        req.data = json.dumps(data).encode()
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            data = json.loads(body) if body else None
            return data, resp.status, resp.headers
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code != 404:
            print(f"  HTTP {e.code} on {url}: {body[:200]}")
        return None, e.code, e.headers


def paginate(url_template, per_page=100):
    items = []
    page = 1
    while True:
        url = url_template.format(per_page=per_page, page=page)
        data, status, headers = github_request("GET", url)
        if data is None:
            break
        if not data:
            break
        items.extend(data)
        if len(data) < per_page:
            break
        page += 1
        remaining = headers.get("X-RateLimit-Remaining", "0")
        if remaining == "0":
            reset = int(headers.get("X-RateLimit-Reset", "0"))
            sleep = max(reset - time.time(), 0) + 2
            print(f"  Rate limited, sleeping {sleep:.0f}s")
            time.sleep(sleep)
    return items


def get_followers(user):
    return paginate(
        f"https://api.github.com/users/{user}/followers?per_page={{per_page}}&page={{page}}"
    )


def get_following(user):
    return paginate(
        f"https://api.github.com/users/{user}/following?per_page={{per_page}}&page={{page}}"
    )


def already_following(user):
    url = f"https://api.github.com/user/following/{user}"
    data, status, headers = github_request("GET", url)
    return status == 204


def follow_user(username):
    url = f"https://api.github.com/user/following/{username}"
    data, status, headers = github_request("PUT", url)
    return status == 204


def load_followed():
    if not os.path.exists(FOLLOW_FILE):
        return set()
    with open(FOLLOW_FILE) as f:
        return {line.strip() for line in f if line.strip()}


def save_followed(followed):
    with open(FOLLOW_FILE, "w") as f:
        for name in sorted(followed):
            f.write(f"{name}\n")


def main():
    tracked = load_followed()
    print(f"Already tracked in {FOLLOW_FILE}: {len(tracked)} users")

    print(f"Fetching followers of {TARGET_USER}...")
    followers = get_followers(TARGET_USER)
    print(f"  Total followers: {len(followers)}")

    target_logins = [f["login"] for f in followers[-MAX_FOLLOW:]]
    print(f"  Last {len(target_logins)} targeted")

    skipped_file = 0
    skipped_already = 0
    followed_count = 0

    for login in target_logins:
        if login in tracked:
            skipped_file += 1
            continue

        if already_following(login):
            skipped_already += 1
            tracked.add(login)
            continue

        print(f"  Following {login}...", end=" ")
        ok = follow_user(login)
        if ok:
            print("OK")
            followed_count += 1
        else:
            print("FAIL")

        tracked.add(login)
        time.sleep(0.5)

    save_followed(tracked)
    print(f"\nDone — followed {followed_count}, skipped (in file) {skipped_file}, skipped (already) {skipped_already}, total tracked {len(tracked)}")


if __name__ == "__main__":
    main()
