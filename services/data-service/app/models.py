"""
Pydantic models for the Data Service.
"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from uuid import uuid4


class DataItemCreate(BaseModel):
    """Request model for creating a data item."""
    title: str = Field(..., min_length=1, max_length=200, description="Item title")
    description: Optional[str] = Field(None, max_length=1000, description="Item description")
    category: str = Field(default="general", description="Item category")
    payload: dict = Field(default_factory=dict, description="Arbitrary data payload")
    priority: str = Field(default="normal", pattern="^(low|normal|high|critical)$")


class DataItemUpdate(BaseModel):
    """Request model for updating a data item."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = None
    payload: Optional[dict] = None
    priority: Optional[str] = Field(None, pattern="^(low|normal|high|critical)$")


class DataItemResponse(BaseModel):
    """Response model for a data item."""
    id: str
    title: str
    description: Optional[str]
    category: str
    payload: dict
    priority: str
    status: str
    created_at: str
    updated_at: str
    processed_at: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated list response."""
    status: str = "success"
    data: list[DataItemResponse]
    pagination: dict


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str
    timestamp: str
    uptime: float
    total_items: int
