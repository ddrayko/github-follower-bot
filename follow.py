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
PER_PAGE = 100

def log(msg):
    print(msg, flush=True)

def github_request(method, url, data=None, quiet=False):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "github-follow-bot",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    if data is not None:
        req.data = json.dumps(data).encode()
    if not quiet:
        log(f"  REQ {method} {url}")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            data = json.loads(body) if body else None
            if not quiet:
                log(f"  RES {resp.status}")
            return data, resp.status, resp.headers
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if not quiet:
            log(f"  RES {e.code} {body[:300]}")
        return None, e.code, e.headers

def already_following(user):
    url = f"https://api.github.com/user/following/{user}"
    data, status, headers = github_request("GET", url, quiet=True)
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

    skipped_file = 0
    skipped_already = 0
    followed_count = 0
    total_processed = 0

    page = 1
    while total_processed < MAX_FOLLOW:
        url = f"https://api.github.com/users/{TARGET_USER}/followers?per_page={PER_PAGE}&page={page}"
        log(f"Fetching followers page {page}...")
        data, status, headers = github_request("GET", url)

        if status != 200:
            log(f"Error {status}, stopping")
            break
        if not data:
            log(f"Empty page {page}, stopping")
            break

        log(f"Got {len(data)} followers from page {page}")

        for entry in data:
            login = entry["login"]
            total_processed += 1

            if total_processed > MAX_FOLLOW:
                log(f"Reached {MAX_FOLLOW} limit, stopping")
                break

            log(f"[{total_processed}/{MAX_FOLLOW}] {login}")

            if login in tracked:
                log(f"  -> SKIP (in follow.txt)")
                skipped_file += 1
                continue

            if already_following(login):
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
            save_followed(tracked)
            time.sleep(0.5)

        remaining = headers.get("X-RateLimit-Remaining", "0")
        log(f"Rate limit remaining: {remaining}")
        if remaining == "0":
            reset = int(headers.get("X-RateLimit-Reset", "0"))
            sleep = max(reset - time.time(), 0) + 2
            log(f"Rate limited, sleeping {sleep:.0f}s")
            time.sleep(sleep)

        page += 1

    save_followed(tracked)
    log(f"\n=== DONE ===")
    log(f"Followed: {followed_count}")
    log(f"Skipped (in file): {skipped_file}")
    log(f"Skipped (already): {skipped_already}")
    log(f"Total tracked: {len(tracked)}")

if __name__ == "__main__":
    main()
