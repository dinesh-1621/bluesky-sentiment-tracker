"""
data_pipeline.py
Streams live posts from Bluesky's Jetstream (a public, no-auth WebSocket
firehose of AT Protocol events), filters by keyword, scores sentiment
with VADER, and writes matches into SQLite.

No API key. No approval process. No rate-limit application queue.
Jetstream is a first-party Bluesky service, publicly hosted, with no
authentication required to connect.

Run this in its own terminal and leave it running:
    python data_pipeline.py
"""

import asyncio
import json
import sqlite3
import time
import re
from datetime import datetime, timezone

import websockets
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

# ---------------------------------------------------------------------------
# CONFIG — edit these
# ---------------------------------------------------------------------------
KEYWORDS = [
    "openai", 
    "apple mobile", 
    "iphone", 
    "apple", 
    "ai"
]  # lowercase; matched as substrings

# Bluesky runs several Jetstream instances for redundancy/load-balancing.
# wantedCollections filters the firehose server-side so we only receive
# "post created" events, not likes/follows/reposts/etc — this cuts bandwidth
# and means our own filtering code only has to look at post text.
JETSTREAM_URL = (
    "wss://jetstream1.us-east.bsky.network/subscribe"
    "?wantedCollections=app.bsky.feed.post"
)

DB_PATH = "sentiment_data.db"

# ---------------------------------------------------------------------------
# One-time NLTK setup (VADER's lexicon needs to be downloaded once)
# ---------------------------------------------------------------------------
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")

analyzer = SentimentIntensityAnalyzer()


def score_sentiment(text: str):
    scores = analyzer.polarity_scores(text)
    compound = scores["compound"]
    if compound >= 0.05:
        label = "Positive"
    elif compound <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"
    return compound, label


def matched_keyword(text: str):
    """Return the first keyword found in the post, or None."""
    for kw in KEYWORDS:
        # \b ensures it only matches whole words, not substrings like "again"
        if re.search(rf"\b{re.escape(kw)}\b", text, re.IGNORECASE):
            return kw
    return None


def insert_post(conn, post_id, text, author_did, keyword, score, label):
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO comments
                (id, text, author, source, keyword_matched,
                 sentiment_score, sentiment_label, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post_id,
                text,
                author_did,      # Bluesky identifies accounts by DID, not
                                 # a simple username — resolving DID -> handle
                                 # requires an extra lookup call, which we skip
                                 # here to keep this a single-connection pipeline.
                "bluesky",
                keyword,
                score,
                label,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    except sqlite3.Error as e:
        # A DB write failure should never take down the stream.
        print(f"[DB ERROR] Could not insert post {post_id}: {e}")


def extract_post_event(raw_message: str):
    """
    Jetstream sends JSON like:
    {
      "did": "did:plc:xxxx",
      "time_us": 1234567890,
      "kind": "commit",
      "commit": {
        "rev": "...",
        "operation": "create",
        "collection": "app.bsky.feed.post",
        "rkey": "abcd1234",
        "record": { "text": "...", "$type": "app.bsky.feed.post", ... },
        "cid": "..."
      }
    }
    We only care about newly created posts, so we filter for
    kind == "commit" and commit.operation == "create".
    Returns (post_id, text, author_did) or None if not a relevant event.
    """
    try:
        event = json.loads(raw_message)
    except json.JSONDecodeError:
        return None

    if event.get("kind") != "commit":
        return None

    commit = event.get("commit", {})
    if commit.get("operation") != "create":
        return None
    if commit.get("collection") != "app.bsky.feed.post":
        return None

    record = commit.get("record", {})
    text = record.get("text")
    if not text:
        return None

    author_did = event.get("did", "unknown")
    post_id = f"{author_did}-{commit.get('rkey', '')}"  # composite unique id

    return post_id, text, author_did


async def run_stream():
    """
    Core streaming loop. Connects to Jetstream over WebSocket and processes
    events as they arrive — this is a genuine push-based stream, not polling:
    Bluesky sends us events the instant they happen, over one persistent
    connection, exactly like the Reddit streaming approach this project
    originally used, but with zero authentication required.
    """
    conn = sqlite3.connect(DB_PATH)
    print(f"Connecting to Bluesky Jetstream...")
    print(f"Filtering for keywords: {KEYWORDS}")

    while True:
        try:
            async with websockets.connect(JETSTREAM_URL, ping_interval=20) as ws:
                print("Connected. Listening for live posts...")
                async for raw_message in ws:
                    result = extract_post_event(raw_message)
                    if result is None:
                        continue

                    post_id, text, author_did = result
                    keyword = matched_keyword(text)
                    if keyword is None:
                        continue  # not relevant, skip

                    score, label = score_sentiment(text)
                    insert_post(conn, post_id, text, author_did, keyword, score, label)
                    print(f"[{label}] ({keyword}) {text[:80]!r}")

        except websockets.exceptions.ConnectionClosed as e:
            print(f"[CONNECTION CLOSED] {e}. Reconnecting in 10s...")
            await asyncio.sleep(10)

        except (OSError, websockets.exceptions.InvalidStatusCode) as e:
            # Network blip or server-side hiccup — back off and retry
            # rather than crashing the whole pipeline.
            print(f"[CONNECTION ERROR] {e}. Reconnecting in 15s...")
            await asyncio.sleep(15)

        except KeyboardInterrupt:
            print("Stream stopped by user.")
            break

        except Exception as e:
            # Catch-all so an unexpected error never silently kills the
            # background pipeline while you're not watching the terminal.
            print(f"[UNEXPECTED ERROR] {e}. Reconnecting in 15s...")
            await asyncio.sleep(15)

    conn.close()


if __name__ == "__main__":
    asyncio.run(run_stream())