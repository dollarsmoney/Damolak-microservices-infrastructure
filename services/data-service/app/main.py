"""
Data Service — FastAPI Application

CRUD microservice for managing data items.
Dispatches processing jobs to the Processing Service (Go)
and sends notifications via the Notification Service.
"""
import time
import logging
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .models import (
    DataItemCreate,
    DataItemUpdate,
    DataItemResponse,
    PaginatedResponse,
    HealthResponse,
)

# ── Structured Logging ────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","service":"%(name)s","message":"%(message)s"}',
)
logger = logging.getLogger(settings.APP_NAME)

# ── In-memory data store ─────────────────────────────
# Production: replace with PostgreSQL/DynamoDB
data_store: dict[str, dict] = {}

START_TIME = time.time()


# ── Lifespan ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Data Service starting on port {settings.PORT}")
    # Seed sample data
    _seed_data()
    yield
    logger.info("Data Service shutting down")


app = FastAPI(
    title="Damolak Data Service",
    version=settings.APP_VERSION,
    description="CRUD microservice for data management",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request ID Middleware ────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Health ───────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow().isoformat(),
        uptime=round(time.time() - START_TIME, 2),
        total_items=len(data_store),
    )


# ── CRUD: List ───────────────────────────────────────
@app.get("/items", response_model=PaginatedResponse)
async def list_items(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
):
    items = list(data_store.values())

    # Filter by category
    if category:
        items = [i for i in items if i["category"] == category]

    # Sort by created_at descending
    items.sort(key=lambda x: x["created_at"], reverse=True)

    # Paginate
    total = len(items)
    offset = (page - 1) * limit
    paginated = items[offset : offset + limit]

    logger.info(f"Listed items: page={page}, limit={limit}, total={total}")

    return PaginatedResponse(
        data=[DataItemResponse(**i) for i in paginated],
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": max(1, -(-total // limit)),  # ceil division
        },
    )


# ── CRUD: Get ────────────────────────────────────────
@app.get("/items/{item_id}", response_model=DataItemResponse)
async def get_item(item_id: str):
    item = data_store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")
    return DataItemResponse(**item)


# ── CRUD: Create ─────────────────────────────────────
@app.post("/items", response_model=DataItemResponse, status_code=201)
async def create_item(body: DataItemCreate):
    item_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    item = {
        "id": item_id,
        "title": body.title,
        "description": body.description,
        "category": body.category,
        "payload": body.payload,
        "priority": body.priority,
        "status": "created",
        "created_at": now,
        "updated_at": now,
        "processed_at": None,
    }
    data_store[item_id] = item

    logger.info(f"Item created: {item_id}, title={body.title}")

    # Dispatch to Processing Service asynchronously
    await _dispatch_to_processor(item)

    # Send notification
    await _send_notification("item_created", item)

    return DataItemResponse(**data_store[item_id])


# ── CRUD: Update ─────────────────────────────────────
@app.put("/items/{item_id}", response_model=DataItemResponse)
async def update_item(item_id: str, body: DataItemUpdate):
    item = data_store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        item[key] = value
    item["updated_at"] = datetime.utcnow().isoformat()

    logger.info(f"Item updated: {item_id}, fields={list(update_data.keys())}")

    return DataItemResponse(**item)


# ── CRUD: Delete ─────────────────────────────────────
@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    if item_id not in data_store:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")

    del data_store[item_id]
    logger.info(f"Item deleted: {item_id}")

    return {"status": "success", "message": f"Item '{item_id}' deleted"}


# ── Processing Callback ─────────────────────────────
@app.post("/items/{item_id}/processed")
async def item_processed_callback(item_id: str, request: Request):
    item = data_store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")

    body = await request.json()
    item["status"] = body.get("status", "processed")
    item["processed_at"] = datetime.utcnow().isoformat()
    item["updated_at"] = item["processed_at"]

    logger.info(f"Item processing complete: {item_id}")
    return {"status": "success"}


# ── Inter-service Communication ──────────────────────
async def _dispatch_to_processor(item: dict):
    """Send item to Processing Service for background work."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.PROCESSING_SERVICE_URL}/process",
                json={
                    "job_id": item["id"],
                    "type": "data_enrichment",
                    "payload": item["payload"],
                    "priority": item["priority"],
                    "callback_url": f"http://data-service:{settings.PORT}/items/{item['id']}/processed",
                },
            )
            item["status"] = "processing"
            logger.info(f"Dispatched to processor: {item['id']}")
    except Exception as e:
        logger.warning(f"Processor dispatch failed: {e}")
        item["status"] = "pending"


async def _send_notification(event_type: str, item: dict):
    """Send event notification to the Notification Service."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                f"{settings.NOTIFICATION_SERVICE_URL}/notify",
                json={
                    "event": event_type,
                    "item_id": item["id"],
                    "title": item["title"],
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
    except Exception as e:
        logger.warning(f"Notification send failed: {e}")


# ── Seed Data ────────────────────────────────────────
def _seed_data():
    """Pre-populate with sample items for demo purposes."""
    samples = [
        {"title": "Infrastructure Audit Report", "category": "reports", "priority": "high"},
        {"title": "Q4 Performance Metrics", "category": "analytics", "priority": "normal"},
        {"title": "Security Compliance Check", "category": "security", "priority": "critical"},
    ]
    for s in samples:
        item_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        data_store[item_id] = {
            "id": item_id,
            "title": s["title"],
            "description": f"Auto-generated seed data for {s['category']}",
            "category": s["category"],
            "payload": {"source": "seed", "auto_generated": True},
            "priority": s["priority"],
            "status": "created",
            "created_at": now,
            "updated_at": now,
            "processed_at": None,
        }
    logger.info(f"Seeded {len(samples)} sample items")
