"""
Wisdom Agent - Wisdom Evaluation Service

Evaluates content against the Wisdom Agent's philosophical framework:
- 7 Universal Values: Awareness, Honesty, Accuracy, Competence,
                      Compassion, Loving-kindness, Joyful-sharing
- Something Deeperism: The philosophical foundation

This is what makes the Wisdom Agent unique among fact-checkers.
We don't just ask "Is it true?" but also "Does it serve wisdom?"

Author: Wisdom Agent Team
Date: 2025-12-20
Phase: 2, Day 10
"""

import json
import logging
import re
from typing import Optional, Dict, Any

from backend.database.connection import get_db_session
from backend.database.fact_check_models import (
    ContentReview, WisdomEvaluation, WisdomVerdict
)

logger = logging.getLogger(__name__)


# ============================================================================
# PHILOSOPHY CONTEXT
# ============================================================================

SOMETHING_DEEPERISM_CONTEXT = """
SOMETHING DEEPERISM (SD) PHILOSOPHY:

Something Deeperism holds that:
1. Humans relate to Truth "poetically" not literally - we can point toward Truth but never fully capture it
2. Pure Love is the foundational reality
3. The 7 Universal Values are behavioral guides that help us align with Pure Love
4. We must acknowledge the limits of human understanding
5. Wisdom involves fostering individual and group wisdom-seeking, not claiming final answers

Content that serves wisdom:
- Acknowledges complexity and uncertainty where appropriate
- Doesn't claim unwarranted certainty about complex truths
- Treats others with respect and compassion
- Seeks to illuminate rather than manipulate
- Invites reflection rather than demanding compliance

Content that serves folly:
- Claims absolute certainty about inherently uncertain matters
- Treats complex truths dogmatically
- Uses manipulation or deception
- Dehumanizes or demeans others
- Squelches inquiry and questioning
"""

SEVEN_VALUES_CONTEXT = """
THE 7 UNIVERSAL VALUES:

1. AWARENESS (1-5 scale)
   - Does the content demonstrate awareness of context, consequences, and complexity?
   - Does it show self-awareness about its own limitations?
   - Is there awareness of how this content affects others?

2. HONESTY (1-5 scale)
   - Is the content honest and transparent about its intentions?
   - Does it avoid deception, even through omission?
   - Does it acknowledge uncertainties rather than hiding them?

3. ACCURACY (1-5 scale)
   - Are factual claims accurate and well-sourced?
   - Are statistics and data used correctly?
   - Are nuances and qualifications preserved?

4. COMPETENCE (1-5 scale)
   - Does the content demonstrate expertise in its subject?
   - Is reasoning sound and methodology appropriate?
   - Are conclusions warranted by the evidence?

5. COMPASSION (1-5 scale)
   - Does the content show care for those affected?
   - Does it consider impact on vulnerable groups?
   - Is criticism constructive rather than cruel?

6. LOVING-KINDNESS (1-5 scale)
   - Does the content promote wellbeing?
   - Does it treat subjects with dignity?
   - Does it seek to build up rather than tear down?

7. JOYFUL-SHARING (1-5 scale)
   - Is knowledge shared generously?
   - Does the content contribute positively to discourse?
   - Is there a spirit of collaborative truth-seeking?

Score each value 1-5:
1 = Actively harmful/absent
2 = Below expectations
3 = Neutral/adequate
4 = Good/above average
5 = Exemplary
"""


# ============================================================================
# PROMPTS
# ============================================================================

WISDOM_EVALUATION_SYSTEM_PROMPT = f"""You are a philosophical evaluator using the Wisdom Agent framework.

{SOMETHING_DEEPERISM_CONTEXT}

{SEVEN_VALUES_CONTEXT}

Your task is to evaluate content against this framework, assessing both:
1. The 7 Universal Values (quantitative scores with qualitative notes)
2. Something Deeperism alignment (does this content serve wisdom or folly?)

Be thorough, fair, and nuanced. Good content can have weaknesses, and problematic content can have strengths. Your goal is illumination, not judgment.

The Three Questions:
1. Is it TRUE? (factual accuracy)
2. Is it REASONABLE? (logical soundness)
3. Does it help humans organize around spiritual Love? (wisdom orientation)

Consider how these three questions interact in each case.

Respond in JSON format only."""

WISDOM_EVALUATION_USER_PROMPT = """Evaluate this content using the Wisdom Agent philosophical framework:

---
{content}
---

FACTUAL CONTEXT (from earlier analysis):
{fact_check_summary}

LOGIC CONTEXT (from earlier analysis):
{logic_summary}

Respond with a JSON object:
{{
  "values_assessment": {{
    "awareness": {{"score": 1-5, "notes": "Explanation"}},
    "honesty": {{"score": 1-5, "notes": "Explanation"}},
    "accuracy": {{"score": 1-5, "notes": "Explanation"}},
    "competence": {{"score": 1-5, "notes": "Explanation"}},
    "compassion": {{"score": 1-5, "notes": "Explanation"}},
    "loving_kindness": {{"score": 1-5, "notes": "Explanation"}},
    "joyful_sharing": {{"score": 1-5, "notes": "Explanation"}}
  }},
  "something_deeperism": {{
    "assessment": "Overall SD assessment narrative",
    "claims_unwarranted_certainty": true/false,
    "treats_complex_truths_dogmatically": true/false,
    "acknowledges_limits_of_understanding": true/false,
    "serves_pure_love": true/false,
    "fosters_or_squelches_sd": "fosters|squelches|neutral"
  }},
  "three_questions": {{
    "is_it_true": "Assessment of factual accuracy",
    "is_it_reasonable": "Assessment of logical soundness",
    "does_it_serve_wisdom": "Assessment of wisdom orientation",
    "interaction": "How do these three interact in this content?"
  }},
  "overall_wisdom_score": 0.0-1.0,
  "serves_wisdom_or_folly": "serves_wisdom|mostly_wise|mixed|mostly_unwise|serves_folly|uncertain",
  "final_reflection": "A thoughtful final reflection integrating all aspects"
}}"""


class WisdomEvaluationError(Exception):
    """Raised when wisdom evaluation fails."""
    pass


class WisdomEvaluationService:
    """
    Service for evaluating content against Wisdom Agent philosophy.
    
    This is what differentiates Wisdom Agent from other fact-checkers.
    We evaluate not just truth and logic, but wisdom - does this content
    serve human flourishing and help us organize around spiritual Love?
    """
    
    def __init__(self, llm_service=None):
        """
        Initialize the wisdom evaluation service.
        
        Args:
            llm_service: Optional LLM service instance
        """
        self._llm_service = llm_service
    
    def get_llm_service(self):
        """Get or create the LLM service."""
        if self._llm_service is None:
            from backend.services.llm_router import get_llm_router
            self._llm_service = get_llm_router()
        return self._llm_service
    
    # ========================================================================
    # MAIN EVALUATION METHOD
    # ========================================================================
    
    async def evaluate_wisdom(
        self,
        review_id: int,
        content: str,
        fact_check_summary: Optional[str] = None,
        logic_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate content against the Wisdom Agent philosophy.
        
        Args:
            review_id: The review ID to store results for
            content: The text content to evaluate
            fact_check_summary: Summary of fact-check findings (optional)
            logic_summary: Summary of logic analysis (optional)
            
        Returns:
            Dict containing wisdom evaluation results
        """
        logger.info(f"Evaluating wisdom for review {review_id}")
        
        if not content or len(content.strip()) < 50:
            logger.warning(f"Content too short for wisdom evaluation: {len(content)} chars")
            return {"error": "Content too short for meaningful wisdom evaluation"}
        
        try:
            # Build context from earlier analyses
            fact_context = fact_check_summary or "No fact-check analysis available."
            logic_context = logic_summary or "No logic analysis available."
            
            # Perform LLM evaluation
            llm = self.get_llm_service()
            
            response = llm.complete(
                messages=[{"role": "user", "content": WISDOM_EVALUATION_USER_PROMPT.format(
                    content=self._truncate_content(content),
                    fact_check_summary=fact_context,
                    logic_summary=logic_context
                )}],
                system_prompt=WISDOM_EVALUATION_SYSTEM_PROMPT,
                temperature=0.4,  # Slightly higher for more nuanced evaluation
            )
            
            # Parse response
            evaluation = self._parse_llm_response(response)
            
            # Save to database
            await self._save_evaluation(review_id, evaluation)
            
            logger.info(f"Wisdom evaluation complete for review {review_id}")
            return evaluation
            
        except Exception as e:
            logger.exception(f"Wisdom evaluation failed for review {review_id}")
            raise WisdomEvaluationError(str(e))
    
    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================
    
    async def _save_evaluation(
        self,
        review_id: int,
        evaluation: Dict[str, Any]
    ):
        """Save wisdom evaluation to the database."""
        with get_db_session() as db:
            # Verify review exists
            review = db.get(ContentReview, review_id)
            if not review:
                raise WisdomEvaluationError(f"Review {review_id} not found")
            
            # Delete existing evaluation if any
            if review.wisdom_evaluation:
                db.delete(review.wisdom_evaluation)
            
            # Extract values
            values = evaluation.get("values_assessment", {})
            sd = evaluation.get("something_deeperism", {})
            three_q = evaluation.get("three_questions", {})
            
            # Map verdict string to enum
            verdict_str = evaluation.get("serves_wisdom_or_folly", "uncertain")
            verdict_map = {
                "serves_wisdom": WisdomVerdict.SERVES_WISDOM,
                "mostly_wise": WisdomVerdict.MOSTLY_WISE,
                "mixed": WisdomVerdict.MIXED,
                "mostly_unwise": WisdomVerdict.MOSTLY_UNWISE,
                "serves_folly": WisdomVerdict.SERVES_FOLLY,
                "uncertain": WisdomVerdict.UNCERTAIN,
            }
            verdict = verdict_map.get(verdict_str.lower(), WisdomVerdict.UNCERTAIN)
            
            # Create evaluation record
            wisdom_eval = WisdomEvaluation(
                review_id=review_id,
                
                # 7 Values scores
                awareness_score=self._extract_score(values.get("awareness")),
                awareness_notes=self._extract_notes(values.get("awareness")),
                honesty_score=self._extract_score(values.get("honesty")),
                honesty_notes=self._extract_notes(values.get("honesty")),
                accuracy_score=self._extract_score(values.get("accuracy")),
                accuracy_notes=self._extract_notes(values.get("accuracy")),
                competence_score=self._extract_score(values.get("competence")),
                competence_notes=self._extract_notes(values.get("competence")),
                compassion_score=self._extract_score(values.get("compassion")),
                compassion_notes=self._extract_notes(values.get("compassion")),
                loving_kindness_score=self._extract_score(values.get("loving_kindness")),
                loving_kindness_notes=self._extract_notes(values.get("loving_kindness")),
                joyful_sharing_score=self._extract_score(values.get("joyful_sharing")),
                joyful_sharing_notes=self._extract_notes(values.get("joyful_sharing")),
                
                # Something Deeperism
                something_deeperism_assessment=sd.get("assessment"),
                claims_unwarranted_certainty=sd.get("claims_unwarranted_certainty"),
                treats_complex_truths_dogmatically=sd.get("treats_complex_truths_dogmatically"),
                acknowledges_limits_of_understanding=sd.get("acknowledges_limits_of_understanding"),
                serves_pure_love=sd.get("serves_pure_love"),
                fosters_or_squelches_sd=sd.get("fosters_or_squelches_sd"),
                
                # Overall
                overall_wisdom_score=self._parse_float(evaluation.get("overall_wisdom_score", 0.5)),
                serves_wisdom_or_folly=verdict,
                final_reflection=evaluation.get("final_reflection"),
                
                # Three questions
                is_it_true_assessment=three_q.get("is_it_true"),
                is_it_reasonable_assessment=three_q.get("is_it_reasonable"),
                does_it_serve_wisdom_assessment=three_q.get("does_it_serve_wisdom"),
                three_questions_interaction=three_q.get("interaction"),
            )
            
            db.add(wisdom_eval)
            
            # Update review with overall wisdom verdict
            review.overall_wisdom_verdict = verdict
            
            db.commit()
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data."""
        try:
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
        
        # Try to find bare JSON
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        logger.warning("Could not parse LLM response as JSON")
        return {
            "values_assessment": {},
            "something_deeperism": {},
            "three_questions": {},
            "overall_wisdom_score": 0.5,
            "serves_wisdom_or_folly": "uncertain",
            "final_reflection": response,
            "parse_error": "Could not parse LLM response"
        }
    
    def _extract_score(self, value_data: Any) -> Optional[int]:
        """Extract score from value assessment."""
        if isinstance(value_data, dict):
            score = value_data.get("score")
            if score is not None:
                try:
                    return max(1, min(5, int(score)))
                except (TypeError, ValueError):
                    pass
        elif isinstance(value_data, (int, float)):
            return max(1, min(5, int(value_data)))
        return None
    
    def _extract_notes(self, value_data: Any) -> Optional[str]:
        """Extract notes from value assessment."""
        if isinstance(value_data, dict):
            return value_data.get("notes")
        return None
    
    def _parse_float(self, value: Any) -> float:
        """Parse and validate a float value."""
        try:
            f = float(value)
            return max(0.0, min(1.0, f))
        except (TypeError, ValueError):
            return 0.5
    
    def _truncate_content(self, content: str, max_chars: int = 10000) -> str:
        """Truncate content to fit within LLM context limits."""
        if len(content) <= max_chars:
            return content
        
        truncated = content[:max_chars]
        
        # Try to break at paragraph
        last_para = truncated.rfind("\n\n")
        if last_para > max_chars * 0.7:
            truncated = truncated[:last_para]
        
        return truncated + "\n\n[Content truncated for evaluation...]"
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def calculate_overall_score(self, values: Dict[str, Any]) -> float:
        """
        Calculate overall wisdom score from individual value scores.
        
        Uses weighted average with emphasis on core values.
        """
        weights = {
            "awareness": 1.0,
            "honesty": 1.2,      # Slightly higher weight
            "accuracy": 1.2,     # Slightly higher weight
            "competence": 1.0,
            "compassion": 1.1,
            "loving_kindness": 1.0,
            "joyful_sharing": 0.9,
        }
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for value_name, weight in weights.items():
            value_data = values.get(value_name, {})
            score = self._extract_score(value_data)
            if score is not None:
                # Normalize 1-5 to 0-1
                normalized = (score - 1) / 4.0
                weighted_sum += normalized * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.5
        
        return weighted_sum / total_weight
    
    def get_value_description(self, value_name: str) -> str:
        """Get description of a value for display."""
        descriptions = {
            "awareness": "Demonstrates awareness of context, consequences, and complexity",
            "honesty": "Honest and transparent about intentions and uncertainties",
            "accuracy": "Factual claims are accurate and well-sourced",
            "competence": "Demonstrates expertise and sound reasoning",
            "compassion": "Shows care for those affected by the content",
            "loving_kindness": "Treats subjects with dignity and promotes wellbeing",
            "joyful_sharing": "Shares knowledge generously and constructively",
        }
        return descriptions.get(value_name, "")
    
    async def quick_wisdom_check(self, text: str) -> Dict[str, Any]:
        """
        Quick wisdom check for shorter content.
        
        Useful for real-time feedback during content creation.
        """
        if len(text) < 50:
            return {"error": "Text too short for evaluation"}
        
        try:
            llm = self.get_llm_service()
            
            response = llm.complete(
                messages=[{"role": "user", "content": text[:2000]}],
                system_prompt="Quickly evaluate this text against wisdom principles. Does it serve wisdom or folly? Respond with JSON: {\"verdict\": \"wise|mixed|unwise\", \"brief_explanation\": \"...\"}",
                temperature=0.3,
            )
            
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"verdict": "uncertain", "brief_explanation": response}
                
        except Exception as e:
            logger.warning(f"Quick wisdom check failed: {e}")
            return {"error": str(e)}


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_wisdom_evaluation_service: Optional[WisdomEvaluationService] = None


def get_wisdom_evaluation_service() -> WisdomEvaluationService:
    """Get or create the wisdom evaluation service instance."""
    global _wisdom_evaluation_service
    if _wisdom_evaluation_service is None:
        _wisdom_evaluation_service = WisdomEvaluationService()
    return _wisdom_evaluation_service
