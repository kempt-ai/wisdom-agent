"""
Wisdom Agent - Claim Extraction Service

Uses LLM to identify and extract claims from content:
- Factual claims (verifiable statements)
- Logical premises and conclusions
- Opinions and emotional appeals (flagged as such)

Author: Wisdom Agent Team
Date: 2025-12-20
Phase: 2, Day 6
"""

import json
import logging
import re
from typing import Optional, List, Dict, Any

from backend.database.connection import get_db_session
from backend.database.fact_check_models import (
    ContentReview, ExtractedClaim, ClaimType
)

logger = logging.getLogger(__name__)


# ============================================================================
# PROMPTS
# ============================================================================

CLAIM_EXTRACTION_SYSTEM_PROMPT = """You are an expert fact-checker and critical thinking analyst. Your task is to extract claims from content that can be fact-checked or logically analyzed.

For each claim you identify:
1. Extract the exact claim as a clear, standalone statement
2. Classify its type (factual, logical, opinion, emotional, mixed)
3. Note where in the content it appears
4. Include the original quote if helpful
5. Rate how "check-worthy" it is (0.0-1.0) based on:
   - Specificity (vague claims are less checkable)
   - Impact (consequential claims matter more)
   - Verifiability (can it be checked against evidence?)

Focus on:
- Statistical claims ("X% of people...")
- Historical claims ("In 1990, X happened...")
- Scientific claims ("Studies show that...")
- Attribution claims ("Expert X said...")
- Causal claims ("X causes Y")
- Comparative claims ("X is better/worse than Y")
- Existence claims ("There is/are X")

DO NOT extract:
- Pure opinions without factual basis
- Obvious truths everyone agrees on
- Subjective preferences
- Future predictions (unless claimed as fact)
- Questions (unless rhetorical with implied claims)

Respond in JSON format only."""

CLAIM_EXTRACTION_USER_PROMPT = """Analyze this content and extract all fact-checkable claims:

---
{content}
---

Respond with a JSON object containing:
{{
  "claims": [
    {{
      "claim_text": "Clear statement of the claim",
      "claim_type": "factual|logical|opinion|emotional|mixed",
      "source_location": "paragraph 1, sentence 2",
      "source_quote": "Original text containing the claim",
      "check_worthiness_score": 0.0-1.0,
      "reasoning": "Brief explanation of why this is check-worthy"
    }}
  ],
  "main_argument": "Brief summary of the content's main argument/thesis",
  "total_claims_found": number
}}

Extract the most important claims (up to 20). Prioritize by check-worthiness."""


class ClaimExtractionError(Exception):
    """Raised when claim extraction fails."""
    pass


class ClaimExtractionService:
    """
    Service for extracting claims from content using LLM.
    
    Identifies:
    - Factual claims that can be verified
    - Logical premises and conclusions
    - Opinions and emotional appeals (flagged as not verifiable)
    """
    
    def __init__(self, llm_service=None):
        """
        Initialize the claim extraction service.
        
        Args:
            llm_service: Optional LLM service instance. If not provided,
                        will use the default LLM router.
        """
        self._llm_service = llm_service
    
    def get_llm_service(self):
        """Get or create the LLM service."""
        if self._llm_service is None:
            # Import here to avoid circular imports
            from backend.services.llm_router import get_llm_router
            self._llm_service = get_llm_router()
        return self._llm_service
    
    # ========================================================================
    # MAIN EXTRACTION METHOD
    # ========================================================================
    
    async def extract_claims(
        self, 
        review_id: int, 
        content: str
    ) -> List[Dict[str, Any]]:
        """
        Extract claims from content for a review.
        
        Args:
            review_id: The review ID to associate claims with
            content: The text content to analyze
            
        Returns:
            List of extracted claims with metadata
        """
        logger.info(f"Extracting claims for review {review_id}")
        
        if not content or len(content.strip()) < 50:
            logger.warning(f"Content too short for claim extraction: {len(content)} chars")
            return []
        
        try:
            # Get LLM response
            llm = self.get_llm_service()
            
            response = llm.complete(
                messages=[{"role": "user", "content": CLAIM_EXTRACTION_USER_PROMPT.format(
                    content=self._truncate_content(content)
                )}],
                system_prompt=CLAIM_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for more consistent extraction
            )
            
            # Parse the response
            claims_data = self._parse_llm_response(response)
            
            # Save claims to database
            saved_claims = await self._save_claims(review_id, claims_data)
            
            logger.info(f"Extracted {len(saved_claims)} claims for review {review_id}")
            return saved_claims
            
        except Exception as e:
            logger.exception(f"Claim extraction failed for review {review_id}")
            raise ClaimExtractionError(str(e))
    
    # ========================================================================
    # RESPONSE PARSING
    # ========================================================================
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data."""
        # Try to extract JSON from the response
        try:
            # First, try direct JSON parse
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find bare JSON object
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        # If all else fails, return empty structure
        logger.warning("Could not parse LLM response as JSON")
        return {"claims": [], "main_argument": None, "total_claims_found": 0}
    
    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================
    
    async def _save_claims(
        self, 
        review_id: int, 
        claims_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Save extracted claims to the database."""
        saved_claims = []
        
        with get_db_session() as db:
            # Verify review exists
            review = db.get(ContentReview, review_id)
            if not review:
                raise ClaimExtractionError(f"Review {review_id} not found")
            
            # Clear any existing claims (in case of re-run)
            for existing_claim in review.claims:
                db.delete(existing_claim)
            
            # Save new claims
            for claim_data in claims_data.get("claims", []):
                try:
                    claim_type = self._parse_claim_type(claim_data.get("claim_type", "factual"))
                    
                    claim = ExtractedClaim(
                        review_id=review_id,
                        claim_text=claim_data.get("claim_text", ""),
                        claim_type=claim_type,
                        source_location=claim_data.get("source_location"),
                        source_quote=claim_data.get("source_quote"),
                        check_worthiness_score=self._parse_score(
                            claim_data.get("check_worthiness_score", 0.5)
                        ),
                    )
                    
                    db.add(claim)
                    saved_claims.append({
                        "claim_text": claim.claim_text,
                        "claim_type": claim.claim_type.value,
                        "source_location": claim.source_location,
                        "source_quote": claim.source_quote,
                        "check_worthiness_score": claim.check_worthiness_score,
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to save claim: {e}")
                    continue
            
            db.commit()
        
        return saved_claims
    
    def _parse_claim_type(self, type_str: str) -> ClaimType:
        """Parse claim type string to enum."""
        type_map = {
            "factual": ClaimType.FACTUAL,
            "logical": ClaimType.LOGICAL,
            "opinion": ClaimType.OPINION,
            "emotional": ClaimType.EMOTIONAL,
            "mixed": ClaimType.MIXED,
        }
        return type_map.get(type_str.lower(), ClaimType.FACTUAL)
    
    def _parse_score(self, score: Any) -> float:
        """Parse and validate a score value."""
        try:
            score = float(score)
            return max(0.0, min(1.0, score))
        except (TypeError, ValueError):
            return 0.5
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _truncate_content(self, content: str, max_chars: int = 15000) -> str:
        """
        Truncate content to fit within LLM context limits.
        
        Tries to truncate at paragraph boundaries.
        """
        if len(content) <= max_chars:
            return content
        
        # Find a good breaking point
        truncated = content[:max_chars]
        
        # Try to break at paragraph
        last_para = truncated.rfind("\n\n")
        if last_para > max_chars * 0.7:  # At least 70% of max
            truncated = truncated[:last_para]
        else:
            # Break at sentence
            last_sentence = max(
                truncated.rfind(". "),
                truncated.rfind(".\n"),
                truncated.rfind("! "),
                truncated.rfind("? "),
            )
            if last_sentence > max_chars * 0.7:
                truncated = truncated[:last_sentence + 1]
        
        return truncated + "\n\n[Content truncated for analysis...]"
    
    # ========================================================================
    # BATCH PROCESSING
    # ========================================================================
    
    async def extract_claims_batch(
        self, 
        review_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Extract claims for multiple reviews.
        
        Returns a dict mapping review_id to extracted claims.
        """
        results = {}
        
        for review_id in review_ids:
            try:
                with get_db_session() as db:
                    review = db.get(ContentReview, review_id)
                    if review:
                        claims = await self.extract_claims(
                            review_id, 
                            review.source_content
                        )
                        results[review_id] = claims
            except Exception as e:
                logger.exception(f"Batch extraction failed for review {review_id}")
                results[review_id] = []
        
        return results


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_claim_extraction_service: Optional[ClaimExtractionService] = None


def get_claim_extraction_service() -> ClaimExtractionService:
    """Get or create the claim extraction service instance."""
    global _claim_extraction_service
    if _claim_extraction_service is None:
        _claim_extraction_service = ClaimExtractionService()
    return _claim_extraction_service
