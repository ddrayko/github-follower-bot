import os
import sys
import json
import time
import urllib.request
import urllib.error

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("GITHUB_TOKEN not set", flush=True)
    sys.exit(1)

BOT_USERNAME = os.environ.get("BOT_USERNAME", "")
FOLLOW_FILE = "follow.txt"
TARGET_USER = "torvalds"
MAX_FOLLOW = 600

def log(msg):
    print(msg, flush=True)

def github_request(method, url, data=None):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-follow-bot",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    if data is not None:
        req.data = json.dumps(data).encode()
    log(f"  REQ {method} {url}")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            data = json.loads(body) if body else None
            log(f"  RES {method} {url} -> {resp.status}")
            return data, resp.status, resp.headers
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        log(f"  RES {method} {url} -> {e.code} {body[:300]}")
        return None, e.code, e.headers

def paginate(url_template, per_page=100):
    items = []
    page = 1
    while True:
        url = url_template.format(per_page=per_page, page=page)
        data, status, headers = github_request("GET", url)
        if status != 200:
            log(f"  paginate: status {status}, stopping")
            break
        if not data:
            log(f"  paginate: empty data, stopping")
            break
        log(f"  paginate: page {page} got {len(data)} items")
        items.extend(data)
        if len(data) < per_page:
            break
        page += 1
        remaining = headers.get("X-RateLimit-Remaining", "0")
        log(f"  rate limit remaining: {remaining}")
        if remaining == "0":
            reset = int(headers.get("X-RateLimit-Reset", "0"))
            sleep = max(reset - time.time(), 0) + 2
            log(f"  rate limited, sleeping {sleep:.0f}s")
            time.sleep(sleep)
    return items

def get_followers(user):
    log(f"Fetching followers of {user}...")
    return paginate(f"https://api.github.com/users/{user}/followers?per_page={per_page}&page={page}")

def get_following(user):
    log(f"Fetching following of {user}...")
    return paginate(f"https://api.github.com/users/{user}/following?per_page={per_page}&page={page}")

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
        log(f"{FOLLOW_FILE} not found, starting fresh")
        return set()
    with open(FOLLOW_FILE) as f:
        lines = {line.strip() for line in f if line.strip()}
    log(f"Loaded {len(lines)} users from {FOLLOW_FILE}")
    return lines

def save_followed(followed):
    with open(FOLLOW_FILE, "w") as f:
        for name in sorted(followed):
            f.write(f"{name}\n")
    log(f"Saved {len(followed)} users to {FOLLOW_FILE}")

def main():
    log("=== START ===")
    log(f"BOT_USERNAME={BOT_USERNAME}, TARGET={TARGET_USER}, MAX={MAX_FOLLOW}")

    tracked = load_followed()

    log("Fetching torvalds followers...")
    followers = get_followers(TARGET_USER)
    log(f"Total followers of {TARGET_USER}: {len(followers)}")

    target_logins = [f["login"] for f in followers[-MAX_FOLLOW:]]
    log(f"Last {len(target_logins)} followers targeted")

    log("Fetching users we already follow...")
    already = {f["login"] for f in get_following(BOT_USERNAME)}
    log(f"Already following: {len(already)} users")

    skipped_file = 0
    skipped_already = 0
    followed_count = 0

    for i, login in enumerate(target_logins, 1):
        log(f"[{i}/{len(target_logins)}] Processing {login}...")

        if login in tracked:
            log(f"  -> SKIP (in follow.txt)")
            skipped_file += 1
            continue

        if login in already:
            log(f"  -> SKIP (already following)")
            skipped_already += 1
            tracked.add(login)
            continue

        ok = follow_user(login)
        if ok:
            log(f"  -> FOLLOWED")
            followed_count += 1
        else:
            log(f"  -> FAILED")

        tracked.add(login)
        time.sleep(0.5)

    save_followed(tracked)
    log(f"\n=== DONE ===")
    log(f"Followed: {followed_count}")
    log(f"Skipped (in file): {skipped_file}")
    log(f"Skipped (already): {skipped_already}")
    log(f"Total tracked: {len(tracked)}")

if __name__ == "__main__":
    main()
