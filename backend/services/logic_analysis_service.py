"""
Wisdom Agent - Logic Analysis Service

Analyzes content for logical structure and fallacies:
- Identifies main conclusion and premises
- Detects logical fallacies
- Assesses argument validity and soundness
- Identifies unstated assumptions

Uses the Logic Analysis Framework from the Wisdom Agent philosophy.

Author: Wisdom Agent Team
Date: 2025-12-20
Phase: 2, Day 9

Modified: 2026-01-15
- Improved system prompt with genre-awareness
- Added steelmanning guidance (charitable interpretation)
- Reduced false positives for rhetorical devices vs actual fallacies
- Calibrated standards to content type (journalism, opinion, academic)

Modified: 2026-01-17
- CRITICAL: Integrated fact-check results into soundness assessment
- Logic analyzer now uses verified claim verdicts instead of treating all premises as uncertain
- Added fact_check_results parameter to analyze_logic()
"""

import json
import logging
import re
from typing import Optional, List, Dict, Any

from backend.database.connection import get_db_session
from backend.database.fact_check_models import ContentReview, LogicAnalysis

logger = logging.getLogger(__name__)


# ============================================================================
# PROMPTS
# ============================================================================

LOGIC_ANALYSIS_SYSTEM_PROMPT = """You are an expert in logic, critical thinking, and argument analysis. Your task is to analyze content for logical structure, validity, and fallacies.

IMPORTANT: Apply PROPORTIONATE STANDARDS based on content type:
- JOURNALISM builds cases from evidence - this is NOT the same as formal logic proof
- OPINION pieces advocate positions - advocacy is NOT automatically fallacious
- ACADEMIC work has higher standards for hedging and methodology
- SOCIAL MEDIA has space constraints - brevity is NOT the same as logical failure

STEELMAN FIRST: Before identifying any fallacy, ask yourself:
"Is there a reasonable interpretation where this is NOT a fallacy?"
Give the author the benefit of the doubt. Your goal is fair analysis, not gotcha detection.

COMMON MISIDENTIFICATIONS TO AVOID:
- Strong language about serious topics ≠ "appeal to emotion"
- Citing expert consensus ≠ "appeal to authority" (it's often appropriate)
- Circumstantial evidence in journalism ≠ logical fallacy (it's standard practice)
- Persuasive writing ≠ manipulation
- Not addressing every counterargument ≠ "straw man"
- Expressing moral judgment ≠ "begging the question"

Your analysis should include:

1. ARGUMENT STRUCTURE
   - Identify the main conclusion (what the author wants you to believe/do)
   - List the explicit premises (reasons given to support the conclusion)
   - Identify unstated assumptions (premises the argument requires but doesn't state)

2. FALLACY DETECTION (with appropriate skepticism)
   Only flag fallacies when you're confident they are ACTUALLY present, not just possible.
   
   RELEVANCE FALLACIES:
   - Ad Hominem: Attacking the person instead of the argument
   - Appeal to Authority: Using authority inappropriately (NOT citing relevant experts)
   - Appeal to Emotion: Using emotion INSTEAD OF logic (NOT using emotion alongside logic)
   - Appeal to Popularity: Claiming truth because many believe it
   - Red Herring: Introducing irrelevant information
   - Straw Man: ACTUALLY misrepresenting someone's argument (NOT just not addressing all aspects)
   
   PRESUMPTION FALLACIES:
   - Begging the Question: LITERALLY assuming what you're trying to prove (NOT just using value-laden language)
   - False Dichotomy: Presenting only two options when more CLEARLY exist
   - Hasty Generalization: Drawing broad conclusions from CLEARLY limited examples
   - Slippery Slope: Claiming one event WILL lead to extreme consequences without justification
   - Circular Reasoning: Using the conclusion as a premise
   
   CAUSAL FALLACIES:
   - False Cause: Claiming causation without sufficient evidence
   - Post Hoc: Assuming temporal sequence implies causation

3. VALIDITY ASSESSMENT
   - Does the conclusion logically follow from the premises (if premises were true)?
   - Consider: In journalistic or opinion contexts, "supporting" a conclusion differs from "proving" it

4. SOUNDNESS ASSESSMENT  
   - Are the premises actually true?
   - Is the logic valid?
   - (Sound = valid logic + true premises)

5. STRENGTHS AND WEAKNESSES
   Note both - good arguments can have weaknesses, weak arguments can have strengths.

6. ALTERNATIVE INTERPRETATIONS
   - What other conclusions could be drawn from the same evidence?
   - What counter-arguments exist?

SEVERITY GUIDANCE:
- "major" = fundamentally undermines the argument
- "moderate" = weakens the argument but doesn't significantly affect the conclusion
- "minor" = worth noting but doesn't significantly affect the conclusion

Be thorough but fair. Err on the side of NOT calling something a fallacy if you're unsure.
Respond in JSON format only."""

# Extended prompt when fact-check results are available
LOGIC_ANALYSIS_SYSTEM_PROMPT_WITH_FACTS = """You are an expert in logic, critical thinking, and argument analysis. Your task is to analyze content for logical structure, validity, and fallacies.

IMPORTANT CONTEXT: You have access to FACT-CHECK RESULTS for key claims in this content. Use these verified verdicts when assessing soundness - do NOT treat verified claims as "uncertain."

IMPORTANT: Apply PROPORTIONATE STANDARDS based on content type:
- JOURNALISM builds cases from evidence - this is NOT the same as formal logic proof
- OPINION pieces advocate positions - advocacy is NOT automatically fallacious
- ACADEMIC work has higher standards for hedging and methodology
- SOCIAL MEDIA has space constraints - brevity is NOT the same as logical failure

STEELMAN FIRST: Before identifying any fallacy, ask yourself:
"Is there a reasonable interpretation where this is NOT a fallacy?"
Give the author the benefit of the doubt. Your goal is fair analysis, not gotcha detection.

COMMON MISIDENTIFICATIONS TO AVOID:
- Strong language about serious topics ≠ "appeal to emotion"
- Citing expert consensus ≠ "appeal to authority" (it's often appropriate)
- Circumstantial evidence in journalism ≠ logical fallacy (it's standard practice)
- Persuasive writing ≠ manipulation
- Not addressing every counterargument ≠ "straw man"
- Expressing moral judgment ≠ "begging the question"

Your analysis should include:

1. ARGUMENT STRUCTURE
   - Identify the main conclusion (what the author wants you to believe/do)
   - List the explicit premises (reasons given to support the conclusion)
   - Identify unstated assumptions (premises the argument requires but doesn't state)

2. FALLACY DETECTION (with appropriate skepticism)
   Only flag fallacies when you're confident they are ACTUALLY present, not just possible.
   
   RELEVANCE FALLACIES:
   - Ad Hominem: Attacking the person instead of the argument
   - Appeal to Authority: Using authority inappropriately (NOT citing relevant experts)
   - Appeal to Emotion: Using emotion INSTEAD OF logic (NOT using emotion alongside logic)
   - Appeal to Popularity: Claiming truth because many believe it
   - Red Herring: Introducing irrelevant information
   - Straw Man: ACTUALLY misrepresenting someone's argument (NOT just not addressing all aspects)
   
   PRESUMPTION FALLACIES:
   - Begging the Question: LITERALLY assuming what you're trying to prove (NOT just using value-laden language)
   - False Dichotomy: Presenting only two options when more CLEARLY exist
   - Hasty Generalization: Drawing broad conclusions from CLEARLY limited examples
   - Slippery Slope: Claiming one event WILL lead to extreme consequences without justification
   - Circular Reasoning: Using the conclusion as a premise
   
   CAUSAL FALLACIES:
   - False Cause: Claiming causation without sufficient evidence
   - Post Hoc: Assuming temporal sequence implies causation

3. VALIDITY ASSESSMENT
   - Does the conclusion logically follow from the premises (if premises were true)?
   - Consider: In journalistic or opinion contexts, "supporting" a conclusion differs from "proving" it

4. SOUNDNESS ASSESSMENT  
   - Use the PROVIDED FACT-CHECK RESULTS to determine if premises are true
   - Claims verified as "true" or "mostly_true" with high confidence should be treated as true premises
   - Claims verified as "false" or "mostly_false" indicate unsound premises
   - Only treat claims as "uncertain" if they were marked "unverifiable" in the fact-check
   - Is the logic valid?
   - (Sound = valid logic + true premises)

5. STRENGTHS AND WEAKNESSES
   Note both - good arguments can have weaknesses, weak arguments can have strengths.

6. ALTERNATIVE INTERPRETATIONS
   - What other conclusions could be drawn from the same evidence?
   - What counter-arguments exist?

SEVERITY GUIDANCE:
- "major" = fundamentally undermines the argument
- "moderate" = weakens the argument but doesn't significantly affect the conclusion
- "minor" = worth noting but doesn't significantly affect the conclusion

Be thorough but fair. Err on the side of NOT calling something a fallacy if you're unsure.
Respond in JSON format only."""

LOGIC_ANALYSIS_USER_PROMPT = """Analyze the logical structure of this content:

---
{content}
---

Respond with a JSON object:
{{
  "main_conclusion": "The primary claim or thesis",
  "premises": [
    "Premise 1: ...",
    "Premise 2: ...",
    "..."
  ],
  "unstated_assumptions": [
    "Assumption 1: ...",
    "..."
  ],
  "fallacies_found": [
    {{
      "name": "Fallacy name",
      "description": "Brief description of this fallacy type",
      "quote": "The specific text exhibiting this fallacy",
      "explanation": "Why this is a fallacy in this context",
      "severity": "minor|moderate|major",
      "confidence": 0.0-1.0
    }}
  ],
  "validity_assessment": {{
    "is_valid": true/false,
    "explanation": "Why the logic is or isn't valid"
  }},
  "soundness_assessment": {{
    "is_sound": true/false/uncertain,
    "explanation": "Assessment of whether premises are true and logic is valid"
  }},
  "alternative_interpretations": [
    "Alternative interpretation 1",
    "..."
  ],
  "strengths": [
    "Strength 1",
    "..."
  ],
  "weaknesses": [
    "Weakness 1",
    "..."
  ],
  "logic_quality_score": 0.0-1.0,
  "confidence": 0.0-1.0
}}"""

# Extended user prompt when fact-check results are available
LOGIC_ANALYSIS_USER_PROMPT_WITH_FACTS = """Analyze the logical structure of this content:

---
{content}
---

FACT-CHECK RESULTS FOR KEY CLAIMS:
{fact_check_summary}

Use these fact-check results when assessing SOUNDNESS. If key premises have been verified as true/mostly_true, the argument's soundness should reflect that verification rather than treating them as uncertain.

Respond with a JSON object:
{{
  "main_conclusion": "The primary claim or thesis",
  "premises": [
    "Premise 1: ...",
    "Premise 2: ...",
    "..."
  ],
  "unstated_assumptions": [
    "Assumption 1: ...",
    "..."
  ],
  "fallacies_found": [
    {{
      "name": "Fallacy name",
      "description": "Brief description of this fallacy type",
      "quote": "The specific text exhibiting this fallacy",
      "explanation": "Why this is a fallacy in this context",
      "severity": "minor|moderate|major",
      "confidence": 0.0-1.0
    }}
  ],
  "validity_assessment": {{
    "is_valid": true/false,
    "explanation": "Why the logic is or isn't valid"
  }},
  "soundness_assessment": {{
    "is_sound": true/false/uncertain,
    "verified_premises": ["List premises confirmed by fact-check"],
    "unverified_premises": ["List premises not covered by fact-check"],
    "false_premises": ["List premises found to be false"],
    "explanation": "Assessment incorporating the fact-check results"
  }},
  "alternative_interpretations": [
    "Alternative interpretation 1",
    "..."
  ],
  "strengths": [
    "Strength 1",
    "..."
  ],
  "weaknesses": [
    "Weakness 1",
    "..."
  ],
  "logic_quality_score": 0.0-1.0,
  "confidence": 0.0-1.0
}}"""


class LogicAnalysisError(Exception):
    """Raised when logic analysis fails."""
    pass


class LogicAnalysisService:
    """
    Service for analyzing logical structure and detecting fallacies.
    
    Uses LLM to perform deep analysis of arguments, identifying:
    - Argument structure (conclusion, premises, assumptions)
    - Logical fallacies with specific examples
    - Validity and soundness assessment
    - Alternative interpretations
    """
    
    # Common fallacy patterns for quick detection
    # NOTE: These are LOW CONFIDENCE indicators - the LLM provides better analysis
    FALLACY_KEYWORDS = {
        "ad_hominem": ["idiot", "stupid", "fool", "moron", "can't trust"],
        "appeal_to_authority": ["experts say", "scientists agree", "studies show"],
        "appeal_to_emotion": ["think of the children", "imagine if", "how would you feel"],
        "false_dichotomy": ["either...or", "only two options", "you're either with us"],
        "slippery_slope": ["next thing you know", "will lead to", "where does it end"],
        "hasty_generalization": ["always", "never", "everyone knows", "all X are"],
    }
    
    def __init__(self, llm_service=None):
        """
        Initialize the logic analysis service.
        
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
    # MAIN ANALYSIS METHOD
    # ========================================================================
    
    async def analyze_logic(
        self,
        review_id: int,
        content: str,
        fact_check_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Perform logic analysis on content.
        
        Args:
            review_id: The review ID to store results for
            content: The text content to analyze
            fact_check_results: Optional list of fact-check results for claims.
                Each result should have 'claim_text', 'verdict', 'confidence', 
                and optionally 'explanation'.
            
        Returns:
            Dict containing analysis results
        """
        logger.info(f"Analyzing logic for review {review_id}")
        
        if not content or len(content.strip()) < 100:
            logger.warning(f"Content too short for logic analysis: {len(content)} chars")
            return {"error": "Content too short for meaningful logic analysis"}
        
        try:
            # Perform LLM analysis
            llm = self.get_llm_service()
            
            # Choose prompts based on whether we have fact-check results
            if fact_check_results and len(fact_check_results) > 0:
                # Build fact-check summary for the prompt
                fact_check_summary = self._format_fact_check_summary(fact_check_results)
                
                system_prompt = LOGIC_ANALYSIS_SYSTEM_PROMPT_WITH_FACTS
                user_prompt = LOGIC_ANALYSIS_USER_PROMPT_WITH_FACTS.format(
                    content=self._truncate_content(content),
                    fact_check_summary=fact_check_summary
                )
                logger.info(f"Logic analysis using {len(fact_check_results)} fact-check results")
            else:
                system_prompt = LOGIC_ANALYSIS_SYSTEM_PROMPT
                user_prompt = LOGIC_ANALYSIS_USER_PROMPT.format(
                    content=self._truncate_content(content)
                )
                logger.info("Logic analysis without fact-check results (soundness will be uncertain)")
            
            response = llm.complete(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                temperature=0.3,
            )
            
            # Parse response
            analysis = self._parse_llm_response(response)
            
            # Quick pattern check for additional fallacies
            # NOTE: These are supplementary and low-confidence
            pattern_fallacies = self._detect_pattern_fallacies(content)
            if pattern_fallacies:
                existing_names = {f.get("name", "").lower() for f in analysis.get("fallacies_found", [])}
                for pf in pattern_fallacies:
                    if pf["name"].lower() not in existing_names:
                        analysis.setdefault("fallacies_found", []).append(pf)
            
            # Add metadata about fact-check integration
            if fact_check_results:
                analysis["fact_check_integrated"] = True
                analysis["fact_check_count"] = len(fact_check_results)
            else:
                analysis["fact_check_integrated"] = False
            
            # Save to database
            await self._save_analysis(review_id, analysis)
            
            logger.info(f"Logic analysis complete for review {review_id}")
            return analysis
            
        except Exception as e:
            logger.exception(f"Logic analysis failed for review {review_id}")
            raise LogicAnalysisError(str(e))
    
    # ========================================================================
    # FACT-CHECK INTEGRATION
    # ========================================================================
    
    def _format_fact_check_summary(
        self, 
        fact_check_results: List[Dict[str, Any]]
    ) -> str:
        """
        Format fact-check results into a readable summary for the LLM prompt.
        
        Args:
            fact_check_results: List of fact-check result dicts
            
        Returns:
            Formatted string summary
        """
        lines = []
        
        for i, result in enumerate(fact_check_results, 1):
            claim = result.get("claim_text", "Unknown claim")
            verdict = result.get("verdict") or "unverifiable"  # Handle None values
            confidence = result.get("confidence") or 0.5  # Handle None values
            explanation = result.get("explanation", "")
            
            # Convert verdict to human-readable (ensure it's a string first)
            verdict_display = str(verdict).replace("_", " ").title()
            confidence_pct = int(confidence * 100)
            
            # Determine if this counts as "verified true" for soundness
            is_verified_true = verdict in ["true", "mostly_true"] and confidence >= 0.7
            is_verified_false = verdict in ["false", "mostly_false"] and confidence >= 0.7
            
            status = ""
            if is_verified_true:
                status = " ✓ VERIFIED"
            elif is_verified_false:
                status = " ✗ FALSE"
            elif verdict == "unverifiable":
                status = " ? UNCERTAIN"
            
            line = f"{i}. \"{claim[:100]}{'...' if len(claim) > 100 else ''}\""
            line += f"\n   Verdict: {verdict_display} ({confidence_pct}% confidence){status}"
            if explanation:
                # Truncate long explanations
                short_explanation = explanation[:200] + "..." if len(explanation) > 200 else explanation
                line += f"\n   Note: {short_explanation}"
            
            lines.append(line)
        
        return "\n\n".join(lines)
    
    # ========================================================================
    # PATTERN-BASED FALLACY DETECTION
    # ========================================================================
    
    def _detect_pattern_fallacies(self, content: str) -> List[Dict[str, Any]]:
        """
        Quick pattern-based fallacy detection.
        
        Supplements LLM analysis with keyword-based detection.
        NOTE: These are LOW CONFIDENCE indicators - patterns alone don't confirm fallacies.
        """
        fallacies = []
        content_lower = content.lower()
        
        for fallacy_type, keywords in self.FALLACY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    # Find the context around the keyword
                    idx = content_lower.find(keyword)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(keyword) + 50)
                    context = content[start:end]
                    
                    fallacies.append({
                        "name": fallacy_type.replace("_", " ").title(),
                        "description": f"Potential {fallacy_type.replace('_', ' ')} detected",
                        "quote": f"...{context}...",
                        "explanation": f"Contains keyword pattern: '{keyword}' (requires human verification)",
                        "severity": "minor",
                        "confidence": 0.3,  # Low confidence for pattern matching
                        "detection_method": "pattern"
                    })
                    break  # One match per fallacy type
        
        return fallacies
    
    # ========================================================================
    # DATABASE OPERATIONS
    # ========================================================================
    
    async def _save_analysis(
        self,
        review_id: int,
        analysis: Dict[str, Any]
    ):
        """Save logic analysis to the database."""
        with get_db_session() as db:
            # Verify review exists
            review = db.get(ContentReview, review_id)
            if not review:
                raise LogicAnalysisError(f"Review {review_id} not found")
            
            # Delete existing analysis if any
            if review.logic_analysis:
                db.delete(review.logic_analysis)
            
            # Create new analysis
            validity = analysis.get("validity_assessment", {})
            soundness = analysis.get("soundness_assessment", {})
            
            logic_analysis = LogicAnalysis(
                review_id=review_id,
                main_conclusion=analysis.get("main_conclusion"),
                premises=analysis.get("premises"),
                unstated_assumptions=analysis.get("unstated_assumptions"),
                fallacies_found=analysis.get("fallacies_found"),
                validity_assessment=validity.get("explanation") if isinstance(validity, dict) else str(validity),
                soundness_assessment=soundness.get("explanation") if isinstance(soundness, dict) else str(soundness),
                alternative_interpretations=analysis.get("alternative_interpretations"),
                logic_quality_score=self._parse_score(analysis.get("logic_quality_score", 0.5)),
                confidence=self._parse_score(analysis.get("confidence", 0.5)),
            )
            
            db.add(logic_analysis)
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
            "main_conclusion": None,
            "premises": [],
            "fallacies_found": [],
            "logic_quality_score": 0.5,
            "confidence": 0.3,
            "parse_error": "Could not parse LLM response"
        }
    
    def _parse_score(self, score: Any) -> float:
        """Parse and validate a score value."""
        try:
            score = float(score)
            return max(0.0, min(1.0, score))
        except (TypeError, ValueError):
            return 0.5
    
    def _truncate_content(self, content: str, max_chars: int = 12000) -> str:
        """Truncate content to fit within LLM context limits."""
        if len(content) <= max_chars:
            return content
        
        truncated = content[:max_chars]
        
        # Try to break at paragraph
        last_para = truncated.rfind("\n\n")
        if last_para > max_chars * 0.7:
            truncated = truncated[:last_para]
        else:
            # Break at sentence
            last_sentence = max(
                truncated.rfind(". "),
                truncated.rfind(".\n"),
            )
            if last_sentence > max_chars * 0.7:
                truncated = truncated[:last_sentence + 1]
        
        return truncated + "\n\n[Content truncated for analysis...]"
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    async def quick_fallacy_check(self, text: str) -> List[Dict[str, Any]]:
        """
        Quick check for obvious fallacies without full analysis.
        
        Useful for real-time feedback during content creation.
        """
        fallacies = self._detect_pattern_fallacies(text)
        
        # Also do a quick LLM check if text is substantial
        if len(text) > 200:
            try:
                llm = self.get_llm_service()
                
                response = llm.complete(
                    messages=[{"role": "user", "content": text[:2000]}],
                    system_prompt="Identify any clear logical fallacies in this text. Be conservative - only flag definite fallacies, not just rhetorical devices. Respond with a JSON array of objects with 'name' and 'quote' fields, or empty array if none found.",
                    temperature=0.3,
                )
                
                try:
                    llm_fallacies = json.loads(response)
                    if isinstance(llm_fallacies, list):
                        fallacies.extend(llm_fallacies)
                except json.JSONDecodeError:
                    pass
                    
            except Exception as e:
                logger.warning(f"Quick LLM fallacy check failed: {e}")
        
        return fallacies
    
    def get_fallacy_explanation(self, fallacy_name: str) -> str:
        """Get a detailed explanation of a fallacy type."""
        explanations = {
            "ad hominem": "Attacking the person making the argument rather than the argument itself. The character or circumstances of the arguer are irrelevant to the truth of their claims.",
            "appeal to authority": "Using an authority figure to support a claim, especially when the authority is not an expert in the relevant field or when experts disagree. Note: Citing relevant expert consensus is generally NOT fallacious.",
            "appeal to emotion": "Using emotional manipulation rather than logical reasoning to convince. Note: Using emotion ALONGSIDE logic is not fallacious - emotion only becomes a fallacy when it REPLACES evidence.",
            "appeal to popularity": "Claiming something is true because many people believe it. Popular belief doesn't determine truth.",
            "false dichotomy": "Presenting only two options when more exist. Also called black-and-white thinking or false dilemma.",
            "slippery slope": "Claiming that one event will inevitably lead to a chain of negative events without adequate justification for each step.",
            "straw man": "Misrepresenting someone's argument to make it easier to attack. Arguing against a weaker version of the actual position.",
            "hasty generalization": "Drawing broad conclusions from a small or unrepresentative sample.",
            "circular reasoning": "Using the conclusion as one of the premises. The argument assumes what it's trying to prove.",
            "begging the question": "Assuming what you're trying to prove. Note: This is NOT the same as 'raising a question' - it means the conclusion is smuggled into the premises.",
            "red herring": "Introducing irrelevant information to distract from the actual issue.",
            "false cause": "Assuming a causal relationship without sufficient evidence. Correlation doesn't imply causation.",
        }
        
        return explanations.get(
            fallacy_name.lower().replace("_", " "),
            "A logical error in reasoning that undermines the argument's validity."
        )


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_logic_analysis_service: Optional[LogicAnalysisService] = None


def get_logic_analysis_service() -> LogicAnalysisService:
    """Get or create the logic analysis service instance."""
    global _logic_analysis_service
    if _logic_analysis_service is None:
        _logic_analysis_service = LogicAnalysisService()
    return _logic_analysis_service
