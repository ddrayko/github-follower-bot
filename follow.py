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
TARGET_USER = "torvalds"
PER_PAGE = 100

DAILY_FOLLOW_LIMIT = 100
DELAY_BETWEEN_FOLLOWS = 30
DELAY_BETWEEN_REQUESTS = 2

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
        if e.code == 403:
            retry_after = e.headers.get("Retry-After")
            if retry_after:
                log(f"  RATE LIMITED, sleeping {retry_after}s")
                time.sleep(int(retry_after))
        return None, e.code, e.headers

def already_following(user):
    url = f"https://api.github.com/user/following/{user}"
    data, status, headers = github_request("GET", url, quiet=True)
    return status == 204

def follow_user(username):
    url = f"https://api.github.com/user/following/{username}"
    data, status, headers = github_request("PUT", url)
    return status == 204

def main():
    log("=== START ===")
    log(f"BOT_USERNAME={BOT_USERNAME}, TARGET={TARGET_USER}")
    log(f"Limits: {DAILY_FOLLOW_LIMIT} follows/day, {DELAY_BETWEEN_FOLLOWS}s between follows")

    skipped_already = 0
    followed_count = 0
    total_processed = 0
    rate_limited = False

    page = 1
    while not rate_limited:
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

            log(f"[{total_processed}] {login}")

            if already_following(login):
                log(f"  -> SKIP (already following)")
                skipped_already += 1
                continue

            if followed_count >= DAILY_FOLLOW_LIMIT:
                log(f"  -> DAILY LIMIT REACHED ({DAILY_FOLLOW_LIMIT}), stopping")
                rate_limited = True
                break

            log(f"  -> Following {login}...")
            ok = follow_user(login)
            if ok:
                log(f"  -> OK")
                followed_count += 1
            else:
                log(f"  -> FAILED")

            log(f"  Waiting {DELAY_BETWEEN_FOLLOWS}s...")
            time.sleep(DELAY_BETWEEN_FOLLOWS)

        if rate_limited:
            break

        remaining = headers.get("X-RateLimit-Remaining", "0")
        log(f"Rate limit remaining: {remaining}")
        if remaining == "0":
            reset = int(headers.get("X-RateLimit-Reset", "0"))
            sleep = max(reset - time.time(), 0) + 2
            log(f"Rate limited, sleeping {sleep:.0f}s")
            time.sleep(sleep)

        page += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)

    log(f"\n=== DONE ===")
    log(f"Followed: {followed_count}")
    log(f"Skipped (already following): {skipped_already}")

if __name__ == "__main__":
    main()
