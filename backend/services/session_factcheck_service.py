"""
Wisdom Agent - Session FactCheck Bridge Service

Connects the Fact & Logic Checker to the session/chat experience.
Allows users to trigger fact-checks during conversations and
view fact-check results in context.

Author: Wisdom Agent Team
Date: 2025-12-21 (Phase 3)
"""

import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionFactCheckService:
    """
    Bridge service connecting fact-checking to chat sessions.
    
    Responsibilities:
    - Trigger fact-checks within session context
    - Link fact-check reviews to sessions
    - Detect check-worthy claims in messages
    - Retrieve fact-checks for a session
    """
    
    def __init__(self):
        self._initialized = False
    
    def initialize(self):
        """Initialize the service."""
        self._initialized = True
        logger.info("SessionFactCheckService initialized")
    
    def is_initialized(self) -> bool:
        return self._initialized
    
    # =========================================
    # Core Operations
    # =========================================
    
    async def trigger_factcheck_in_session(
        self,
        session_id: int,
        content: str,
        source_type: str = "text",
        source_url: Optional[str] = None,
        title: Optional[str] = None,
        auto_triggered: bool = False,
        user_id: int = 1  # TODO: Get from auth context
    ) -> Dict[str, Any]:
        """
        Trigger a fact-check within a session context.
        
        This creates a fact-check review linked to the session and
        starts the analysis pipeline.
        
        Args:
            session_id: The session to link the fact-check to
            content: The content to fact-check (text or will be fetched from URL)
            source_type: "text" or "url"
            source_url: URL if source_type is "url"
            title: Optional title for the review
            auto_triggered: Whether this was auto-detected vs user-requested
            user_id: The user initiating the fact-check
            
        Returns:
            Dict with review_id, status, and poll_url
        """
        try:
            # Import here to avoid circular dependencies
            from backend.services.review_service import get_review_service
            from backend.models.review_models import ReviewCreateRequest
            from backend.database.fact_check_models import SourceType
            
            review_service = get_review_service()
            
            # Generate title if not provided
            if not title:
                if source_type == "url" and source_url:
                    title = f"Fact-check: {source_url[:50]}..."
                else:
                    title = f"Fact-check: {content[:50]}..."
            
            # Determine source type enum
            if source_type == "url":
                src_type = SourceType.URL
            else:
                src_type = SourceType.TEXT
            
            # Create request object matching the existing interface
            request = ReviewCreateRequest(
                source_type=src_type,
                source_content=content if source_type == "text" else None,
                source_url=source_url if source_type == "url" else None,
                title=title,
                session_id=session_id,
                project_id=None
            )
            
            # Create the review (this is async)
            review_response = await review_service.create_review(request)
            review_id = review_response.id
            
            # Start the analysis (runs in background)
            # Note: run_analysis is async, we don't await it to return quickly
            import asyncio
            asyncio.create_task(review_service.run_analysis(review_id))
            
            return {
                "review_id": review_id,
                "status": "processing",
                "message_id": None,  # Could add fact-check message support later
                "poll_url": f"/api/reviews/{review_id}/status",
                "auto_triggered": auto_triggered
            }
            
        except Exception as e:
            logger.error(f"Failed to trigger fact-check in session {session_id}: {e}")
            raise
    
    async def get_session_factchecks(
        self,
        session_id: int,
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Get all fact-checks associated with a session.
        
        Args:
            session_id: The session ID
            include_details: If True, include full review details
            
        Returns:
            Dict with session_id, factchecks list, and total count
        """
        try:
            from backend.services.review_service import get_review_service
            
            review_service = get_review_service()
            
            # Get reviews for this session (this method already exists!)
            reviews = await review_service.get_reviews_for_session(session_id)
            
            factchecks = []
            for review in reviews:
                factcheck_data = {
                    "review_id": review.id,
                    "status": review.status.value if hasattr(review.status, 'value') else str(review.status),
                    "created_at": review.created_at.isoformat() if review.created_at else None,
                    "title": review.title,
                    "source_type": review.source_type.value if hasattr(review.source_type, 'value') else str(review.source_type),
                    "quick_summary": review.quick_summary,
                    "overall_factual_verdict": review.overall_factual_verdict.value if review.overall_factual_verdict and hasattr(review.overall_factual_verdict, 'value') else None,
                    "overall_wisdom_verdict": review.overall_wisdom_verdict.value if review.overall_wisdom_verdict and hasattr(review.overall_wisdom_verdict, 'value') else None
                }
                
                if include_details:
                    # Get full review details
                    full_review = await review_service.get_review(review.id)
                    if full_review:
                        factcheck_data["details"] = full_review.dict() if hasattr(full_review, 'dict') else full_review
                
                factchecks.append(factcheck_data)
            
            return {
                "session_id": session_id,
                "factchecks": factchecks,
                "total": len(factchecks)
            }
            
        except Exception as e:
            logger.error(f"Failed to get fact-checks for session {session_id}: {e}")
            return {
                "session_id": session_id,
                "factchecks": [],
                "total": 0,
                "error": str(e)
            }
    
    # =========================================
    # Claim Detection
    # =========================================
    
    def detect_factcheck_intent(self, message: str) -> Dict[str, Any]:
        """
        Detect if a message contains a fact-check request or checkworthy claim.
        
        Returns:
            Dict with:
            - has_intent: bool - Whether fact-checking was requested
            - intent_type: str - "explicit_request", "url_shared", "claim_detected", None
            - claim_text: str - The claim to check (if detected)
            - url: str - URL to check (if detected)
            - confidence: float - How confident we are in detection
        """
        result = {
            "has_intent": False,
            "intent_type": None,
            "claim_text": None,
            "url": None,
            "confidence": 0.0
        }
        
        message_lower = message.lower().strip()
        
        # Pattern 1: Explicit fact-check requests
        explicit_patterns = [
            r"fact[\s-]?check\s+(?:this|that|the following)?[:\s]*(.+)",
            r"is\s+it\s+true\s+that\s+(.+)",
            r"can\s+you\s+(?:verify|check)\s+(?:if|whether|that)?\s*(.+)",
            r"verify\s+(?:this|that)?[:\s]*(.+)",
            r"check\s+(?:if|whether)\s+(.+)",
            r"is\s+(?:this|that)\s+(?:true|accurate|correct)[:\s]*(.+)?",
        ]
        
        for pattern in explicit_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                claim = match.group(1) if match.lastindex else message
                result["has_intent"] = True
                result["intent_type"] = "explicit_request"
                result["claim_text"] = claim.strip() if claim else message
                result["confidence"] = 0.9
                return result
        
        # Pattern 2: URL detection
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, message)
        if urls:
            result["has_intent"] = True
            result["intent_type"] = "url_shared"
            result["url"] = urls[0]
            result["confidence"] = 0.7
            return result
        
        # Pattern 3: Claims with hedging language (lower confidence)
        hedging_patterns = [
            r"i\s+(?:read|heard|saw)\s+that\s+(.+)",
            r"(?:they|people)\s+say\s+that\s+(.+)",
            r"apparently[,]?\s+(.+)",
            r"supposedly[,]?\s+(.+)",
        ]
        
        for pattern in hedging_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                result["has_intent"] = True
                result["intent_type"] = "claim_detected"
                result["claim_text"] = match.group(1).strip()
                result["confidence"] = 0.5
                return result
        
        return result
    
    def should_suggest_factcheck(self, message: str) -> Dict[str, Any]:
        """
        Determine if we should suggest fact-checking to the user.
        
        Returns:
            Dict with should_suggest, reason, and suggested_claim
        """
        detection = self.detect_factcheck_intent(message)
        
        # If explicit request, don't suggest - just do it
        if detection["intent_type"] == "explicit_request":
            return {
                "should_suggest": False,
                "reason": "explicit_request",
                "suggested_claim": None,
                "suggestion_text": None
            }
        
        # If URL shared, suggest checking
        if detection["intent_type"] == "url_shared":
            return {
                "should_suggest": True,
                "reason": "url_shared",
                "suggested_claim": detection["url"],
                "suggestion_text": "I notice you shared a URL. Would you like me to fact-check this article?"
            }
        
        # If claim detected with hedging language, suggest
        if detection["intent_type"] == "claim_detected" and detection["confidence"] >= 0.5:
            claim_preview = detection["claim_text"][:100] + "..." if len(detection["claim_text"]) > 100 else detection["claim_text"]
            return {
                "should_suggest": True,
                "reason": "uncertain_claim",
                "suggested_claim": detection["claim_text"],
                "suggestion_text": f"I can fact-check the claim: \"{claim_preview}\" Would you like me to verify this?"
            }
        
        return {
            "should_suggest": False,
            "reason": "no_checkworthy_content",
            "suggested_claim": None,
            "suggestion_text": None
        }


# =========================================
# Singleton Pattern
# =========================================

_service_instance: Optional[SessionFactCheckService] = None


def get_session_factcheck_service() -> SessionFactCheckService:
    """Get or create the singleton service instance."""
    global _service_instance
    
    if _service_instance is None:
        _service_instance = SessionFactCheckService()
        _service_instance.initialize()
    
    return _service_instance
