#!/usr/bin/env python3
"""
CyberGuard Labs — 24/7 Cloud Autopilot Runner
Runs in GitHub Actions environment without requiring local computer to be on.
1. Submits daily IndexNow freshness signals to search engines.
2. Automatically rotates and publishes high-converting X (Twitter) deal threads via API v2.
3. Automatically tracks history and state in git.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MATRIX_FILE = REPO_ROOT / "data" / "x_tweet_content_matrix.json"
HISTORY_FILE = REPO_ROOT / "data" / "x_posted_history.jsonl"

def resolve_image_path(raw_path):
    if not raw_path:
        return None
    p = Path(raw_path)
    candidates = [
        p,
        REPO_ROOT / p,
        REPO_ROOT / "assets" / "infographics" / p.name,
        REPO_ROOT / "pinterest_assets" / p.name
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None

def task_ping_indexnow():
    print("=" * 60)
    print("🌐 Task 1: Submitting IndexNow Search Engine Freshness Signals...")
    print("=" * 60)
    
    url = "https://api.indexnow.org/indexnow"
    payload = {
        "host": "lab.gkismet.com",
        "key": "e4f507b9a71b4a929d2bf9f738a19de0",
        "keyLocation": "https://lab.gkismet.com/e4f507b9a71b4a929d2bf9f738a19de0.txt",
        "urlList": [
            "https://lab.gkismet.com/switchbot/",
            "https://lab.gkismet.com/deals/",
            "https://lab.gkismet.com/reviews/",
            "https://lab.gkismet.com/best-self-cleaning-litter-box-2026/",
            "https://lab.gkismet.com/petkit-pura-max-vs-litter-robot-4/",
            "https://lab.gkismet.com/petkit-pura-max-review/",
            "https://lab.gkismet.com/surfshark-vs-nordvpn/",
            "https://lab.gkismet.com/nordpass-vs-1password/"
        ]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"✅ IndexNow Response Status: {resp.status} (Freshness Boost Active!)")
            return True
    except Exception as e:
        print(f"⚠️ IndexNow Ping Note: {e}")
        return False

def task_publish_next_x_thread():
    print("\n" + "=" * 60)
    print("🐦 Task 2: Checking X (Twitter) Next Deal Thread...")
    print("=" * 60)
    
    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")
    
    if not all([api_key, api_secret, access_token, access_token_secret]):
        print("💡 Note: X API credentials not detected in GitHub Secrets.")
        print("   To enable 24/7 automated tweeting, add these in GitHub Repo Settings -> Secrets:")
        print("   • X_API_KEY")
        print("   • X_API_SECRET")
        print("   • X_ACCESS_TOKEN")
        print("   • X_ACCESS_TOKEN_SECRET")
        print("   Skipping X automated post for this run.")
        return False

    try:
        from requests_oauthlib import OAuth1Session
    except ImportError:
        print("❌ Error: requests_oauthlib is required for X API. Install via pip.")
        return False

    if not MATRIX_FILE.exists():
        print(f"❌ Error: Matrix file not found at {MATRIX_FILE}")
        return False

    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        matrix = json.load(f)

    posted_ids = set()
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        record = json.loads(line)
                        posted_ids.add(record.get("id"))
                    except Exception:
                        pass

    target_item = None
    for item in matrix:
        if item["id"] not in posted_ids:
            target_item = item
            break

    if not target_item:
        print("🎉 Notice: All threads in matrix have been posted! Resetting or waiting for new content.")
        return False

    print(f"🎯 Target Thread Selected: {target_item['id']} ({target_item.get('target_product')})")
    oauth = OAuth1Session(
        client_key=api_key,
        client_secret=api_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret
    )

    # 1. Upload Media
    media_id = None
    resolved_img = resolve_image_path(target_item.get("media_path"))
    if resolved_img:
        print(f"🖼️ Uploading infographic: {resolved_img}...")
        try:
            with open(resolved_img, "rb") as mf:
                resp = oauth.post("https://upload.twitter.com/1.1/media/upload.json", files={"media": mf})
                if resp.status_code in [200, 201, 202]:
                    media_id = resp.json().get("media_id_string")
                    print(f"✅ Media uploaded successfully! ID: {media_id}")
                else:
                    print(f"⚠️ Media upload error: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"⚠️ Media upload exception: {e}")

    # 2. Post Hook Tweet
    api_url = "https://api.twitter.com/2/tweets"
    hook_payload = {"text": target_item["hook_tweet"]}
    if media_id:
        hook_payload["media"] = {"media_ids": [media_id]}

    print("🚀 Publishing Hook Tweet...")
    r = oauth.post(api_url, json=hook_payload)
    if r.status_code not in [200, 201]:
        print(f"❌ Failed to publish Hook Tweet: {r.status_code} - {r.text}")
        return False

    first_tweet_id = r.json()["data"]["id"]
    tweet_ids = [first_tweet_id]
    print(f"✅ Hook Tweet published! ID: {first_tweet_id}")
    time.sleep(2)

    # 3. Post Thread Replies
    last_id = first_tweet_id
    for idx, reply_text in enumerate(target_item.get("thread_tweets", []), 1):
        reply_payload = {
            "text": reply_text,
            "reply": {"in_reply_to_tweet_id": last_id}
        }
        r_rep = oauth.post(api_url, json=reply_payload)
        if r_rep.status_code in [200, 201]:
            last_id = r_rep.json()["data"]["id"]
            tweet_ids.append(last_id)
            print(f"✅ Thread Tweet {idx} published! ID: {last_id}")
            time.sleep(2)
        else:
            print(f"⚠️ Thread Tweet {idx} error: {r_rep.status_code} - {r_rep.text}")
            break

    # 4. Record history
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "id": target_item["id"],
            "target_product": target_item.get("target_product"),
            "tweet_ids": tweet_ids,
            "tweet_url": f"https://x.com/cyberguardlabs/status/{first_tweet_id}",
            "timestamp": int(time.time()),
            "status": "PUBLISHED"
        }) + "\n")

    print(f"🎉 Thread completed! Total tweets published: {len(tweet_ids)}")
    return True

def main():
    print("🚀 Starting CyberGuard Labs Cloud Autopilot Runner...")
    
    # Run Task 1: IndexNow Freshness Signals
    task_ping_indexnow()
    
    # Run Task 2: X (Twitter) Next Deal Thread
    has_posted = task_publish_next_x_thread()

    # Output for GitHub Actions
    github_output = os.getenv("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"has_new_post={'true' if has_posted else 'false'}\n")

    print("🏁 Autopilot Execution Finished Successfully!")

if __name__ == "__main__":
    main()
