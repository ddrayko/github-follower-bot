# github-follower-bot

Educational GitHub Action bot that automatically follows a target user's followers, with rate-limit handling and persistent tracking via `follow.txt`.

> [!WARNING]
> This project is for **educational purposes only**. Automated following may violate [GitHub's Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) and could result in account restrictions, rate limiting, or suspension. **Use at your own risk.**

## How it works

- Fetches the followers of a target GitHub user.
- Follows accounts that aren't already followed, tracking progress in `follow.txt`.
- Respects a configurable daily follow limit and delay between requests.
- Handles GitHub API rate limiting automatically.
- Runs on a schedule via GitHub Actions.

## Configuration

Environment variables:

| Variable | Description |
|---|---|
| `PAT_TOKEN` | Personal access token with `user:follow` scope |
| `BOT_USERNAME` | The account running the bot |

Script constants (in `follow.py`):

| Variable | Description |
|---|---|
| `TARGET_USER` | The user whose followers will be followed |
| `DAILY_FOLLOW_LIMIT` | Max follows per run |
| `DELAY_BETWEEN_FOLLOWS` | Delay (seconds) between each follow action |

## License

MIT
