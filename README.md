# 🔴🟡🟢 Bluesky Sentiment Tracker

A real-time sentiment tracker for [Bluesky](https://bsky.app) posts. It streams live posts from Bluesky's public **Jetstream** firehose, filters them by keyword, scores sentiment with **VADER**, stores results in SQLite, and visualizes everything on a live-refreshing **Streamlit** dashboard.

No API key, no approval process, and no rate-limited application queue required — Jetstream is a first-party, publicly hosted Bluesky service.

## Features

- 🔌 Connects directly to Bluesky's Jetstream WebSocket firehose (no auth needed)
- 🔍 Filters posts by configurable keywords
- 🧠 Scores each matched post's sentiment using NLTK's VADER analyzer
- 💾 Persists results to a local SQLite database (WAL mode for concurrent read/write)
- 📊 Live Streamlit dashboard with:
  - Sentiment trend line chart
  - Sentiment distribution pie chart
  - Topic/keyword filter
  - Scrolling live post feed with sentiment icons
- ♻️ Auto-reconnect logic if the stream drops

## Project Structure

```
.
├── app.py              # Streamlit dashboard (reads from the DB)
├── data_pipeline.py    # Streams posts, filters, scores, writes to DB
├── setup_db.py         # One-time DB initialization
├── clear_db.py         # Utility to wipe old data from the DB
├── requirements.txt    # Python dependencies

```

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/dinesh-1621/bluesky-sentiment-tracker.git
cd bluesky-sentiment-tracker
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv my_env
# Windows
my_env\Scripts\activate
# macOS/Linux
source my_env/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize the database
Run this once:
```bash
python setup_db.py
```

## Running the App

You'll need **two terminals** running at the same time (both with the virtual environment activated).

**Terminal 1 — start the data pipeline** (keep this running in the background):
```bash
python data_pipeline.py
```

**Terminal 2 — start the dashboard:**
```bash
streamlit run app.py
```

The dashboard will open in your browser and auto-refresh every 7 seconds.

## Configuration

Edit the `KEYWORDS` list at the top of `data_pipeline.py` to change which topics are tracked:

```python
KEYWORDS = [
    "openai",
    "apple mobile",
    "iphone",
    "apple",
    "ai"
]
```

## Resetting the Data

To clear all captured posts and start fresh:
```bash
python clear_db.py
```

## Notes

- Bluesky identifies accounts by DID (not username); resolving a DID to a readable handle requires an extra API lookup, which this project skips to keep the pipeline lightweight and single-connection.
- The dashboard reads from `sentiment_data.db`, which is only populated while `data_pipeline.py` is running.

