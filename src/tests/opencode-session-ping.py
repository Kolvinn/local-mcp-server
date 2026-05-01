import sqlite3
import json
import os
import time
import logging
from datetime import datetime

# Path to the OpenCode production database
DB_PATH = os.path.expanduser("~/.local/share/opencode/opencode.db")

# Mapping the JSON modelID slugs to our Pricing/TTL table
MODEL_MAP = {
    "deepseek-v4-pro": "DeepSeek V4 Pro",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
    "minimax-m2.7": "MiniMax M2.7",
    "kimi-k2.6": "Kimi K2.6",
    "glm-5.1": "GLM-5.1"
}

# The 2026 OpenCode Go Rate Card
PRICING = {
    "DeepSeek V4 Pro": {"inj": 1.74, "read": 0.145, "out": 3.48, "ttl": 10},
    "DeepSeek V4 Flash": {"inj": 0.15, "read": 0.015, "out": 0.40, "ttl": 10},
    "MiniMax M2.7": {"inj": 0.30, "read": 0.030, "out": 1.20, "ttl": 10},
    "Kimi K2.6": {"inj": 0.75, "read": 0.125, "out": 1.50, "ttl": 60}
}

def analyze_sessions():
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) # Open as Read-Only
        cursor = conn.cursor()

        # Start of day in milliseconds (OpenCode uses ms timestamps)
        today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)

        query = """
        WITH LatestMessages AS (
            SELECT session_id, MAX(time_updated) as last_time
            FROM message
            WHERE time_updated >= ?
            GROUP BY session_id
        )
        SELECT m.session_id, m.data, m.time_updated
        FROM message m
        JOIN LatestMessages lm ON m.session_id = lm.session_id AND m.time_updated = lm.last_time
        """
        
        cursor.execute(query, (today_start,))
        rows = cursor.fetchall()
        
        results = []
        for session_id, data_json, last_active_ms in rows:
            data = json.loads(data_json)
            
            # Extract dynamics from the "data" column JSON
            model_slug = data.get("modelID")
            input_tokens = data.get("tokens", {}).get("input", 0)
            model_name = MODEL_MAP.get(model_slug)
            
            if not model_name or model_name not in PRICING:
                continue

            last_active_sec = last_active_ms / 1000
            time_since_active_min = (time.time() - last_active_sec) / 60
            
            # Decision Logic
            metrics = PRICING[model_name]
            should_ping = False
            
            # 1. Check TTL: If we are 2 minutes away from expiry
            if time_since_active_min >= (metrics["ttl"] - 2) and time_since_active_min < metrics["ttl"]:
                # 2. Math Check: Is it cheaper to keep 50k tokens alive than to re-inject?
                cost_cold = (input_tokens / 1e6) * metrics["inj"]
                cost_ping = (input_tokens / 1e6) * metrics["read"]
                
                # If pinging is 5x cheaper than cold starting, we keep it alive
                if cost_ping < (cost_cold / 5):
                    should_ping = True
            
            results.append({
                "session": session_id,
                "model": model_name,
                "tokens": input_tokens,
                "idle_min": round(time_since_active_min, 1),
                "action": "PING" if should_ping else "IGNORE"
            })
            
        conn.close()
        return results

    except Exception as e:
        return f"Error accessing DB: {e}"

# Run Analysis
session_report = analyze_sessions()
print(json.dumps(session_report, indent=4))