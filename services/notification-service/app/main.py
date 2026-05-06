"""
Notification Service — Flask Application

Receives event notifications from other microservices and logs them.
In production, this would integrate with:
  - Amazon SES for email
  - Amazon SNS for push notifications
  - Slack/Teams webhooks
  - WebSocket connections for real-time UI updates

For this implementation, notifications are logged to stdout (CloudWatch)
and stored in-memory for retrieval via the API.
"""
import os
import time
import uuid
import logging
from datetime import datetime
from collections import deque

from flask import Flask, request, jsonify

# ── Configuration ────────────────────────────────────
APP_NAME = "damolak-notification-service"
APP_VERSION = "1.0.0"
PORT = int(os.getenv("PORT", "5000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MAX_NOTIFICATIONS = 1000  # Ring buffer size

# ── Logging (JSON for CloudWatch) ────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","service":"notification-service","message":"%(message)s"}',
)
logger = logging.getLogger(APP_NAME)

# ── Application ─────────────────────────────────────
app = Flask(__name__)
start_time = time.time()

# Ring buffer for recent notifications
notifications = deque(maxlen=MAX_NOTIFICATIONS)

# Stats
stats = {
    "total_received": 0,
    "total_by_event": {},
    "total_by_channel": {"log": 0, "webhook": 0, "email": 0},
}


# ── Health ───────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": APP_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": round(time.time() - start_time, 2),
        "notifications_stored": len(notifications),
        "total_processed": stats["total_received"],
    })


# ── Send Notification ────────────────────────────────
@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "JSON body required"}), 400

    event = data.get("event", "unknown")
    item_id = data.get("item_id", "N/A")
    title = data.get("title", "N/A")
    channel = data.get("channel", "log")
    timestamp = data.get("timestamp", datetime.utcnow().isoformat())

    # Build notification record
    notification = {
        "id": str(uuid.uuid4()),
        "event": event,
        "item_id": item_id,
        "title": title,
        "channel": channel,
        "message": _build_message(event, title, item_id),
        "timestamp": timestamp,
        "received_at": datetime.utcnow().isoformat(),
        "status": "delivered",
    }

    # Store in ring buffer
    notifications.appendleft(notification)

    # Update stats
    stats["total_received"] += 1
    stats["total_by_event"][event] = stats["total_by_event"].get(event, 0) + 1
    stats["total_by_channel"][channel] = stats["total_by_channel"].get(channel, 0) + 1

    # Dispatch to channel
    _dispatch_notification(notification, channel)

    logger.info(
        f"Notification sent: event={event} item_id={item_id} channel={channel}"
    )

    return jsonify({
        "status": "success",
        "notification_id": notification["id"],
        "channel": channel,
        "message": notification["message"],
    }), 201


# ── Bulk Notify ──────────────────────────────────────
@app.route("/notify/bulk", methods=["POST"])
def bulk_notify():
    data = request.get_json(silent=True)
    if not data or "notifications" not in data:
        return jsonify({"status": "error", "message": "notifications array required"}), 400

    results = []
    for item in data["notifications"]:
        event = item.get("event", "unknown")
        notification = {
            "id": str(uuid.uuid4()),
            "event": event,
            "item_id": item.get("item_id", "N/A"),
            "title": item.get("title", "N/A"),
            "channel": item.get("channel", "log"),
            "message": _build_message(event, item.get("title", "N/A"), item.get("item_id", "N/A")),
            "timestamp": datetime.utcnow().isoformat(),
            "received_at": datetime.utcnow().isoformat(),
            "status": "delivered",
        }
        notifications.appendleft(notification)
        stats["total_received"] += 1
        results.append({"id": notification["id"], "event": event})

    logger.info(f"Bulk notification: {len(results)} items processed")

    return jsonify({
        "status": "success",
        "processed": len(results),
        "results": results,
    }), 201


# ── List Notifications ───────────────────────────────
@app.route("/notifications", methods=["GET"])
def list_notifications():
    page = int(request.args.get("page", 1))
    limit = min(int(request.args.get("limit", 20)), 100)
    event_filter = request.args.get("event")

    items = list(notifications)

    if event_filter:
        items = [n for n in items if n["event"] == event_filter]

    total = len(items)
    offset = (page - 1) * limit
    paginated = items[offset:offset + limit]

    return jsonify({
        "status": "success",
        "data": paginated,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": max(1, -(-total // limit)),
        },
    })


# ── Stats ────────────────────────────────────────────
@app.route("/stats", methods=["GET"])
def get_stats():
    return jsonify({
        "status": "success",
        "data": {
            **stats,
            "notifications_in_buffer": len(notifications),
            "buffer_capacity": MAX_NOTIFICATIONS,
        },
    })


# ── Helper Functions ─────────────────────────────────
def _build_message(event, title, item_id):
    """Build a human-readable notification message."""
    templates = {
        "item_created": f"📦 New item created: '{title}' (ID: {item_id})",
        "item_updated": f"✏️ Item updated: '{title}' (ID: {item_id})",
        "item_deleted": f"🗑️ Item deleted: '{title}' (ID: {item_id})",
        "processing_complete": f"✅ Processing complete for: '{title}' (ID: {item_id})",
        "processing_failed": f"❌ Processing failed for: '{title}' (ID: {item_id})",
        "user_registered": f"👤 New user registered: '{title}'",
        "user_login": f"🔐 User logged in: '{title}'",
    }
    return templates.get(event, f"📬 Event '{event}' for item '{title}' (ID: {item_id})")


def _dispatch_notification(notification, channel):
    """
    Dispatch notification to the appropriate channel.
    In production, this would send actual emails, webhooks, etc.
    Currently logs to stdout for CloudWatch capture.
    """
    if channel == "log":
        logger.info(f"[LOG] {notification['message']}")
    elif channel == "webhook":
        logger.info(f"[WEBHOOK] Would POST to webhook: {notification['message']}")
    elif channel == "email":
        logger.info(f"[EMAIL] Would send email: {notification['message']}")
    else:
        logger.info(f"[{channel.upper()}] {notification['message']}")


# ── 404 Handler ──────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "status": "error",
        "message": f"Route not found: {request.url}",
    }), 404


# ── Entry Point ──────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"Notification Service starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
