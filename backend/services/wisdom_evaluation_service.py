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

Modified: 2026-01-03
- Added external philosophy file loading from data/philosophy/wisdom_evaluation_philosophy.txt
- Philosophy can now be edited without touching code
- Added reload_philosophy() function for future UI editing support

Modified: 2026-01-15
- Added sd_mini.txt loading for modular grounding
- Philosophy now loaded in two parts: SD grounding + task-specific instructions
- SD mini is loaded FIRST, then wisdom evaluation instructions

Modified: 2026-01-17
- Added genre detection for genre-appropriate evaluation standards
- Op-eds now evaluated as opinion pieces, not strict journalism
- Fixed: Advocacy is not manipulation; making a case is not dishonest
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any

from backend.database.connection import get_db_session
from backend.database.fact_check_models import (
    ContentReview, WisdomEvaluation, WisdomVerdict
)

logger = logging.getLogger(__name__)


# ============================================================================
# PHILOSOPHY FILE LOADING
# ============================================================================

# Cache for loaded philosophy content
_SD_MINI_CONTENT: Optional[str] = None
_WISDOM_EVAL_CONTENT: Optional[str] = None
_PHILOSOPHY_CONTENT: Optional[str] = None


def _find_philosophy_file(filename: str) -> Optional[Path]:
    """
    Find a philosophy file in the expected locations.
    
    Args:
        filename: The name of the file to find (e.g., 'sd_mini.txt')
        
    Returns:
        Path to the file if found, None otherwise
    """
    possible_paths = [
        # From backend/services/ go up two levels to project root, then into data/philosophy/base/
        Path(__file__).parent.parent.parent / "data" / "philosophy" / "base" / filename,
        # Direct path from project root (with base/ subdirectory)
        Path(f"data/philosophy/base/{filename}"),
        # Docker container path (with base/ subdirectory)
        Path(f"/app/data/philosophy/base/{filename}"),
        # Fallback: try without base/ subdirectory (legacy locations)
        Path(__file__).parent.parent.parent / "data" / "philosophy" / filename,
        Path(f"data/philosophy/{filename}"),
        Path(f"/app/data/philosophy/{filename}"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    return None


def load_sd_mini_content() -> str:
    """
    Load the Something Deeperism mini-grounding from sd_mini.txt.
    
    This provides the philosophical foundation that should be loaded
    BEFORE any task-specific instructions.
    
    File location: data/philosophy/sd_mini.txt
    """
    path = _find_philosophy_file("sd_mini.txt")
    
    if path:
        try:
            content = path.read_text(encoding='utf-8')
            logger.info(f"Loaded SD mini-grounding from: {path}")
            return content
        except Exception as e:
            logger.warning(f"Could not read {path}: {e}")
    
    logger.warning("sd_mini.txt not found, SD grounding will be minimal")
    return ""


def load_wisdom_eval_content() -> str:
    """
    Load philosophy content from the external text file.
    
    This allows the philosophy to be edited without touching Python code.
    Falls back to embedded defaults if the file is not found.
    
    File location: data/philosophy/wisdom_evaluation_philosophy.txt
    """
    path = _find_philosophy_file("wisdom_evaluation_philosophy.txt")
    
    if path:
        try:
            content = path.read_text(encoding='utf-8')
            logger.info(f"Loaded wisdom evaluation philosophy from: {path}")
            return content
        except Exception as e:
            logger.warning(f"Could not read {path}: {e}")
    
    logger.warning("Philosophy file not found, using embedded defaults")
    return _get_default_philosophy()


# Keep the old function name for backwards compatibility
def load_philosophy_content() -> str:
    """
    Load philosophy content from the external text file.
    
    DEPRECATED: Use load_wisdom_eval_content() instead.
    Kept for backwards compatibility.
    """
    return load_wisdom_eval_content()


def _get_default_philosophy() -> str:
    """
    Embedded fallback if external file not found.
    
    This ensures the service works even without the external file,
    but you should use the external file for customization.
    """
    return """
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

THE 7 UNIVERSAL VALUES (1-5 scale):

1. AWARENESS - context and self-awareness
2. HONESTY - transparency and truthfulness  
3. ACCURACY - factual correctness
4. COMPETENCE - expertise and sound reasoning
5. COMPASSION - care for those affected
6. LOVING-KINDNESS - dignity and wellbeing
7. JOYFUL-SHARING - generous knowledge sharing

THE THREE QUESTIONS:
1. Is it TRUE? (factual accuracy)
2. Is it REASONABLE? (logical soundness)
3. Does it serve WISDOM? (alignment with Pure Love)
"""


def get_sd_mini_content() -> str:
    """Get cached SD mini content, loading if necessary."""
    global _SD_MINI_CONTENT
    if _SD_MINI_CONTENT is None:
        _SD_MINI_CONTENT = load_sd_mini_content()
    return _SD_MINI_CONTENT


def get_wisdom_eval_content() -> str:
    """Get cached wisdom evaluation content, loading if necessary."""
    global _WISDOM_EVAL_CONTENT
    if _WISDOM_EVAL_CONTENT is None:
        _WISDOM_EVAL_CONTENT = load_wisdom_eval_content()
    return _WISDOM_EVAL_CONTENT


def get_philosophy_content() -> str:
    """
    Get combined philosophy content: SD mini-grounding + wisdom evaluation instructions.
    
    This is the main function called by the system prompt generator.
    Loads SD mini first (the grounding), then wisdom evaluation instructions.
    """
    global _PHILOSOPHY_CONTENT
    if _PHILOSOPHY_CONTENT is None:
        sd_mini = get_sd_mini_content()
        wisdom_eval = get_wisdom_eval_content()
        
        # Combine with clear separation if both exist
        if sd_mini:
            _PHILOSOPHY_CONTENT = f"{sd_mini}\n\n{'='*60}\n\n{wisdom_eval}"
        else:
            _PHILOSOPHY_CONTENT = wisdom_eval
    
    return _PHILOSOPHY_CONTENT


def reload_philosophy() -> str:
    """
    Force reload of philosophy content from file.
    
    Call this if the file has been edited and you want to pick up changes
    without restarting the service. Useful for future UI editing feature.
    
    Returns:
        The newly loaded philosophy content
    """
    global _SD_MINI_CONTENT, _WISDOM_EVAL_CONTENT, _PHILOSOPHY_CONTENT
    _SD_MINI_CONTENT = None
    _WISDOM_EVAL_CONTENT = None
    _PHILOSOPHY_CONTENT = None
    content = get_philosophy_content()
    logger.info(f"Philosophy reloaded ({len(content)} characters)")
    return content


# ============================================================================
# GENRE DETECTION
# ============================================================================

def detect_content_genre(content: str, title: str = "") -> str:
    """
    Detect the genre of content for genre-appropriate evaluation.
    
    This is CRITICAL for fair evaluation. An op-ed should not be judged
    by the standards of a news report, and vice versa.
    
    Args:
        content: The text content to analyze
        title: Optional title for additional context
        
    Returns:
        One of: 'opinion_editorial', 'journalism', 'academic', 'social_informal', 'unknown'
    """
    content_lower = content.lower()
    title_lower = title.lower() if title else ""
    combined = f"{title_lower} {content_lower[:2000]}"  # Check first 2000 chars
    
    # Opinion/Editorial indicators
    opinion_signals = [
        # Explicit labels
        "opinion", "editorial", "op-ed", "oped", "commentary", "column",
        "perspective", "viewpoint", "analysis",
        # First-person advocacy
        "i believe", "i think", "in my view", "it seems to me",
        "we should", "we must", "we need to",
        # Argumentative framing
        "the real problem is", "what this means is", "the truth is",
        "make no mistake", "let's be clear", "here's why",
        # Value judgments
        "shameful", "outrageous", "unacceptable", "dangerous",
        "coercion", "shakedown", "corruption", "abuse of power",
    ]
    
    # News/Journalism indicators  
    journalism_signals = [
        # Attribution patterns
        "according to", "sources say", "officials said", "reported that",
        "in a statement", "declined to comment", "did not respond",
        # News structure
        "breaking:", "update:", "developing:",
        "who, what, when, where",
        # Neutral framing
        "on one hand", "critics say", "supporters argue",
    ]
    
    # Academic indicators
    academic_signals = [
        "abstract", "methodology", "findings suggest", "the data shows",
        "peer-reviewed", "citation", "et al.", "hypothesis",
        "statistically significant", "p-value", "confidence interval",
        "literature review", "theoretical framework",
    ]
    
    # Social/Informal indicators
    social_signals = [
        "lol", "tbh", "imo", "imho", "thread:", "🧵",
        "@", "#", "retweet", "share if you",
    ]
    
    # Count signals
    opinion_count = sum(1 for signal in opinion_signals if signal in combined)
    journalism_count = sum(1 for signal in journalism_signals if signal in combined)
    academic_count = sum(1 for signal in academic_signals if signal in combined)
    social_count = sum(1 for signal in social_signals if signal in combined)
    
    # Determine genre based on strongest signals
    max_count = max(opinion_count, journalism_count, academic_count, social_count)
    
    if max_count == 0:
        return "unknown"
    
    if opinion_count == max_count and opinion_count >= 2:
        return "opinion_editorial"
    elif academic_count == max_count and academic_count >= 2:
        return "academic"
    elif social_count == max_count and social_count >= 2:
        return "social_informal"
    elif journalism_count == max_count and journalism_count >= 2:
        return "journalism"
    elif opinion_count >= 2:  # Default to opinion if signals present
        return "opinion_editorial"
    else:
        return "unknown"


def get_genre_guidance(genre: str) -> str:
    """
    Get genre-specific evaluation guidance.
    
    This ensures evaluators apply appropriate standards for each content type.
    """
    guidance = {
        "opinion_editorial": """
GENRE: OPINION/EDITORIAL
This content is an OPINION PIECE. Apply these standards:
- Primary job: Argue for a position with evidence and reasoning
- IT IS APPROPRIATE TO: Advocate strongly, use persuasive language, express value judgments
- NOT REQUIRED TO: Present opposing views equally, pretend neutrality, exhaustively caveat
- REMEMBER: Advocacy ≠ manipulation. Making a case is not dishonest.
- A WISE op-ed: Argues fairly, engages counterarguments where relevant, doesn't dehumanize opponents
- Strong language about serious matters (e.g., "coercion," "shakedowns") is APPROPRIATE if supported by evidence
- Score of 3 = adequate for this genre; reserve low scores for genuine problems
""",
        "journalism": """
GENRE: NEWS JOURNALISM  
This content is NEWS REPORTING. Apply these standards:
- Primary job: Inform readers about what happened
- IT IS APPROPRIATE TO: Report facts, quote sources, build cases from evidence
- NOT REQUIRED TO: Exhaustively caveat every claim, present all alternatives equally
- Circumstantial evidence IS legitimate in journalism
- A WISE news article: Accurately informs, cites sources, distinguishes confirmed from alleged
- Score of 3 = adequate for this genre
""",
        "academic": """
GENRE: ACADEMIC/SCHOLARLY
This content is ACADEMIC WORK. Apply these standards:
- Primary job: Advance knowledge through rigorous inquiry
- REQUIRED TO: Cite sources, acknowledge limitations, engage prior work
- Held to HIGHER standards of methodology and hedging than other genres
- A WISE academic paper: Sound methodology, appropriate hedging, honest about limitations
""",
        "social_informal": """
GENRE: SOCIAL/INFORMAL
This content is CASUAL/SOCIAL MEDIA. Apply these standards:
- Primary job: Share, connect, communicate quickly
- Space constraints are real; exhaustive sourcing is unrealistic
- A WISE social post: Shares helpfully, doesn't spread clear misinformation, doesn't punch down
- Be LENIENT on format while still assessing substance
""",
        "unknown": """
GENRE: GENERAL CONTENT
Genre could not be determined. Apply balanced standards:
- Assess based on what the content appears to be trying to accomplish
- Give benefit of the doubt on stylistic choices
- Focus on substance over form
"""
    }
    return guidance.get(genre, guidance["unknown"])


# ============================================================================
# SYSTEM PROMPT GENERATION
# ============================================================================

def get_wisdom_evaluation_system_prompt(genre: str = "unknown") -> str:
    """
    Generate the system prompt using loaded philosophy content and genre guidance.
    
    Args:
        genre: The detected genre of the content being evaluated
        
    This is called fresh each time to allow for hot-reloading of philosophy.
    """
    philosophy = get_philosophy_content()
    genre_guidance = get_genre_guidance(genre)
    
    return f"""You are a philosophical evaluator using the Wisdom Agent framework.

{philosophy}

{genre_guidance}

CRITICAL EVALUATION PRINCIPLES:
1. Apply GENRE-APPROPRIATE standards - an op-ed is not a news report
2. A score of 3 means "adequate for this content type" - not every piece needs 5s
3. Strong advocacy with evidence is NOT the same as manipulation
4. Assess what the content IS, not what you wish it were
5. Reserve low scores (1-2) for genuine problems, not stylistic preferences

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


# ============================================================================
# USER PROMPT (kept as constant - structure shouldn't change)
# ============================================================================

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
        logic_summary: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate content against the Wisdom Agent philosophy.
        
        Args:
            review_id: The review ID to store results for
            content: The text content to evaluate
            fact_check_summary: Summary of fact-check findings (optional)
            logic_summary: Summary of logic analysis (optional)
            title: Optional title for better genre detection
            
        Returns:
            Dict containing wisdom evaluation results
        """
        logger.info(f"Evaluating wisdom for review {review_id}")
        
        if not content or len(content.strip()) < 50:
            logger.warning(f"Content too short for wisdom evaluation: {len(content)} chars")
            return {"error": "Content too short for meaningful wisdom evaluation"}
        
        try:
            # Detect content genre for appropriate evaluation standards
            genre = detect_content_genre(content, title or "")
            logger.info(f"Detected genre for review {review_id}: {genre}")
            
            # Build context from earlier analyses
            fact_context = fact_check_summary or "No fact-check analysis available."
            logic_context = logic_summary or "No logic analysis available."
            
            # Perform LLM evaluation
            llm = self.get_llm_service()
            
            # Use dynamic system prompt with genre-specific guidance
            response = llm.complete(
                messages=[{"role": "user", "content": WISDOM_EVALUATION_USER_PROMPT.format(
                    content=self._truncate_content(content),
                    fact_check_summary=fact_context,
                    logic_summary=logic_context
                )}],
                system_prompt=get_wisdom_evaluation_system_prompt(genre=genre),
                temperature=0.4,  # Slightly higher for more nuanced evaluation
            )
            
            # Parse response
            evaluation = self._parse_llm_response(response)
            
            # Add genre to evaluation for transparency
            evaluation["detected_genre"] = genre
            
            # Save to database
            await self._save_evaluation(review_id, evaluation)
            
            logger.info(f"Wisdom evaluation complete for review {review_id} (genre: {genre})")
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
    
    def get_philosophy_path(self) -> Optional[str]:
        """
        Get the path to the loaded philosophy file.
        
        Returns None if using embedded defaults.
        Useful for the UI to show where the philosophy is coming from.
        """
        path = _find_philosophy_file("wisdom_evaluation_philosophy.txt")
        return str(path) if path else None
    
    def get_philosophy_paths(self) -> Dict[str, Optional[str]]:
        """
        Get paths to all loaded philosophy files.
        
        Returns dict with paths or None if using embedded defaults.
        Useful for the UI to show where the philosophy is coming from.
        """
        sd_path = _find_philosophy_file("sd_mini.txt")
        eval_path = _find_philosophy_file("wisdom_evaluation_philosophy.txt")
        
        return {
            "sd_mini": str(sd_path) if sd_path else None,
            "wisdom_evaluation": str(eval_path) if eval_path else None,
        }


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
