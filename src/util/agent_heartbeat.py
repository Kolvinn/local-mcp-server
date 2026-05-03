import os
import time
import json
import logging
import requests
from datetime import datetime, timedelta

# --- Configuration ---
API_KEY = os.getenv("OPENCODE_API_KEY", "your_api_key_here")
SESSION_DIR = "./.agents/sessions"  # Where your agent TUI saves active contexts
MODEL_CACHE_FILE = ".opencode_models.json"
REFRESH_INTERVAL_HOURS = 24
HEARTBEAT_LOOP_SECONDS = 60  # Check sessions every minute

# Setup Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [HEARTBEAT] - %(message)s"
)


def fetch_pricing_data():
    """
    Fetches model pricing and TTL from OpenCode Go docs/API.
    Uses a local JSON cache to avoid pulling data every minute.
    """
    if os.path.exists(MODEL_CACHE_FILE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(MODEL_CACHE_FILE))
        if datetime.now() - file_mod_time < timedelta(hours=REFRESH_INTERVAL_HOURS):
            with open(MODEL_CACHE_FILE, "r") as f:
                return json.load(f)

    logging.info("Refreshing model pricing from opencode.ai/docs/go...")

    # In a real 2026 OpenCode environment, this hits the pricing JSON endpoint.
    # We provide the fallback hardcoded state if the API is unreachable.
    fallback_data = {
        "DeepSeek V4 Pro": {"inj": 1.74, "read": 0.145, "out": 3.48, "ttl_min": 10},
        "DeepSeek V4 Flash": {"inj": 0.15, "read": 0.015, "out": 0.40, "ttl_min": 10},
        "MiniMax M2.7": {"inj": 0.30, "read": 0.030, "out": 1.20, "ttl_min": 10},
        "Kimi K2.6": {"inj": 0.75, "read": 0.125, "out": 1.50, "ttl_min": 60},
        "GLM-5.1": {"inj": 1.05, "read": 0.205, "out": 5.00, "ttl_min": 15},
    }

    try:
        # Conceptual API endpoint for OpenCode Go 2026
        response = requests.get("https://opencode.ai/zen/go/v1/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            with open(MODEL_CACHE_FILE, "w") as f:
                f.writelines(json.dumps(data))
            return data
    except requests.RequestException:
        logging.warning("API unreachable. Using fallback 2026 rate card.")
        with open(MODEL_CACHE_FILE, "w") as f:
            json.dump(fallback_data, f)
        return fallback_data


def should_ping(
    model_data, context_tokens, time_since_last_msg_min, expected_away_time_min=60
):
    """
    The Core Mathematical Breakpoint Engine.
    Determines if maintaining the cache is cheaper than a cold start.
    """
    ttl = model_data["ttl_min"]

    # If we are safely inside the TTL window, do nothing yet.
    if time_since_last_msg_min < (ttl - 2):
        return False, "TTL Safe"

    # Calculate costs per 1M tokens
    ctx_millions = context_tokens / 1_000_000
    cost_cold = ctx_millions * model_data["inj"]

    # A ping is a read + a tiny 10-token output
    cost_ping = (ctx_millions * model_data["read"]) + (
        (10 / 1_000_000) * model_data["out"]
    )

    # How many pings needed to survive the expected away time?
    num_pings_needed = expected_away_time_min // (ttl - 1)
    if num_pings_needed == 0:
        num_pings_needed = 1

    total_maintenance_cost = cost_ping * num_pings_needed

    if total_maintenance_cost < cost_cold:
        return True, f"Ping Cheaper (${total_maintenance_cost:.4f} < ${cost_cold:.4f})"
    else:
        return False, f"Let Expire (${total_maintenance_cost:.4f} > ${cost_cold:.4f})"


def send_silent_ping(session_id, model_name):
    """
    Dispatches the exact zero-context-bloat ping to the OpenCode API.
    """
    logging.info(f"-> Executing Silent Ping for Session: {session_id} ({model_name})")

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    payload = {
        "model": model_name,
        "session_id": session_id,
        "messages": [
            {
                "role": "system",
                "content": "[SYSTEM_SIGNAL]: CACHE_REFRESH_ONLY. DO NOT OUTPUT TEXT. ACKNOWLEDGE WITH A SINGLE PERIOD.",
            }
        ],
        "max_tokens": 1,
    }

    try:
        # Conceptual ping endpoint
        requests.post(
            "https://opencode.ai/api/go/v1/chat/completions",
            json=payload,
            headers=headers,
        )
    except Exception as e:
        logging.error(f"Failed to ping {session_id}: {e}")


def get_active_sessions():
    """
    Scans your local project directory for active OpenCode TUI sessions.
    Returns a list of dicts: [{'id': '...', 'model': '...', 'tokens': 45000, 'last_active': timestamp}]
    """
    sessions = []
    if not os.path.exists(SESSION_DIR):
        return sessions

    for filename in os.listdir(SESSION_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(SESSION_DIR, filename)
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    # Extract last modified time as last active time
                    last_active = os.path.getmtime(filepath)
                    sessions.append(
                        {
                            "id": data.get("session_id", filename.split(".")[0]),
                            "model": data.get("model", "DeepSeek V4 Flash"),
                            "tokens": data.get("current_context_tokens", 0),
                            "last_active": last_active,
                        }
                    )
            except Exception:
                pass
    return sessions


def run_daemon():
    logging.info("Starting OpenCode Go Heartbeat Daemon...")
    while True:
        pricing_data = fetch_pricing_data()
        sessions = get_active_sessions()

        now = time.time()

        for session in sessions:
            model_name = session["model"]
            if model_name not in pricing_data:
                continue

            model_metrics = pricing_data[model_name]
            minutes_inactive = (now - session["last_active"]) / 60.0

            # Skip if context is tiny (under 8k tokens)
            if session["tokens"] < 8000:
                continue

            do_ping, reason = should_ping(
                model_data=model_metrics,
                context_tokens=session["tokens"],
                time_since_last_msg_min=minutes_inactive,
                expected_away_time_min=60,  # Assumes a standard 1-hour away time
            )

            if do_ping:
                send_silent_ping(session["id"], model_name)
                # Touch the session file so we don't ping it again immediately
                os.utime(os.path.join(SESSION_DIR, f"{session['id']}.json"), None)
            else:
                if "TTL Safe" not in reason:
                    logging.debug(
                        f"Session {session['id']} ({model_name}) ignored: {reason}"
                    )

        time.sleep(HEARTBEAT_LOOP_SECONDS)


if __name__ == "__main__":
    fetch_pricing_data()
