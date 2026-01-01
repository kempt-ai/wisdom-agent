"""
Wisdom Agent - Session FactCheck Models

Pydantic models for fact-check integration with sessions.

Author: Wisdom Agent Team
Date: 2025-12-21 (Phase 3)
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class FactCheckSourceType(str, Enum):
    """Source type for fact-check content."""
    TEXT = "text"
    URL = "url"


class TriggerFactCheckRequest(BaseModel):
    """Request to trigger a fact-check within a session."""
    
    content: str = Field(
        ...,
        description="The content to fact-check (claim text or URL)",
        min_length=10,
        max_length=50000
    )
    source_type: FactCheckSourceType = Field(
        default=FactCheckSourceType.TEXT,
        description="Type of content: 'text' for direct claims, 'url' for articles"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="URL to fact-check (required if source_type is 'url')"
    )
    title: Optional[str] = Field(
        default=None,
        description="Optional title for the fact-check review",
        max_length=200
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "content": "The Great Wall of China is visible from space",
                    "source_type": "text",
                    "title": "Space visibility claim"
                },
                {
                    "content": "https://example.com/article",
                    "source_type": "url",
                    "source_url": "https://example.com/article"
                }
            ]
        }


class TriggerFactCheckResponse(BaseModel):
    """Response after triggering a fact-check."""
    
    review_id: int = Field(..., description="ID of the created fact-check review")
    status: str = Field(..., description="Current status (usually 'processing')")
    message_id: Optional[int] = Field(
        default=None,
        description="ID of the fact-check message created in the session"
    )
    poll_url: str = Field(..., description="URL to poll for status updates")
    auto_triggered: bool = Field(
        default=False,
        description="Whether this was auto-detected vs user-requested"
    )


class SessionFactCheckSummary(BaseModel):
    """Summary of a fact-check within a session."""
    
    review_id: int
    status: str
    created_at: Optional[str] = None
    title: Optional[str] = None
    source_type: str
    quick_summary: Optional[str] = None
    overall_factual_verdict: Optional[str] = None
    overall_wisdom_verdict: Optional[str] = None
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Full review details (if requested)"
    )


class SessionFactChecksResponse(BaseModel):
    """Response containing all fact-checks for a session."""
    
    session_id: int
    factchecks: List[SessionFactCheckSummary] = []
    total: int = 0
    error: Optional[str] = None


class DetectionResult(BaseModel):
    """Result of fact-check intent detection."""
    
    has_intent: bool = Field(
        ...,
        description="Whether a fact-check intent was detected"
    )
    intent_type: Optional[str] = Field(
        default=None,
        description="Type: 'explicit_request', 'url_shared', 'claim_detected', or None"
    )
    claim_text: Optional[str] = Field(
        default=None,
        description="The claim text extracted (if applicable)"
    )
    url: Optional[str] = Field(
        default=None,
        description="URL detected (if applicable)"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the detection"
    )


class SuggestionResult(BaseModel):
    """Result of fact-check suggestion analysis."""
    
    should_suggest: bool = Field(
        ...,
        description="Whether to suggest fact-checking to the user"
    )
    reason: str = Field(
        ...,
        description="Reason for suggestion or lack thereof"
    )
    suggested_claim: Optional[str] = Field(
        default=None,
        description="The claim or URL to suggest checking"
    )
    suggestion_text: Optional[str] = Field(
        default=None,
        description="Human-readable suggestion text"
    )


class AnalyzeMessageRequest(BaseModel):
    """Request to analyze a message for fact-check potential."""
    
    content: str = Field(
        ...,
        description="The message content to analyze",
        min_length=1
    )


class AnalyzeMessageResponse(BaseModel):
    """Response from message analysis."""
    
    detection: DetectionResult
    suggestion: SuggestionResult
