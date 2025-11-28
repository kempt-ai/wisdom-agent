"""
Wisdom Agent - Reflection Service

Handles session summaries, self-reflection using the 7 Universal Values,
and evolving meta-summaries that track wisdom development across sessions.

The 7 Universal Values:
1. Awareness - Staying present to what's actually happening
2. Honesty - Truth-telling even when difficult  
3. Accuracy - Precision in understanding and communication
4. Competence - Doing things well and skillfully
5. Compassion - Meeting all beings and their suffering with care
6. Loving-kindness - Active goodwill toward everyone
7. Joyful-sharing - Generosity and celebration of the good

Migrated from summary_manager.py with new config system integration.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from backend.config import config


# Singleton instance
_reflection_service: Optional['ReflectionService'] = None


class ReflectionService:
    """Manages session summaries, self-reflection, and meta-summaries."""
    
    # The 7 Universal Values
    UNIVERSAL_VALUES = [
        "Awareness",
        "Honesty", 
        "Accuracy",
        "Competence",
        "Compassion",
        "Loving-kindness",
        "Joyful-sharing"
    ]
    
    def __init__(self, llm_router, philosophy_text: Optional[str] = None):
        """
        Initialize the Reflection Service.
        
        Args:
            llm_router: LLMRouter instance for generating reflections
            philosophy_text: Optional base philosophy text for grounding
        """
        self.llm_router = llm_router
        self.philosophy_text = philosophy_text or ""
        self.meta_summary_file = config.DATA_DIR / "memory" / "meta_summary.json"
        
        # Ensure directory exists
        self.meta_summary_file.parent.mkdir(parents=True, exist_ok=True)
    
    def generate_session_summary(
        self,
        session_id: int,
        messages: List[Dict],
        reflection_text: str = "",
        previous_summaries: Optional[List[Dict]] = None
    ) -> Tuple[str, Dict]:
        """
        Generate a comprehensive summary of the session.
        
        Args:
            session_id: Unique session identifier
            messages: Conversation messages
            reflection_text: WA's self-reflection on the session
            previous_summaries: Optional list of recent session summaries
            
        Returns:
            Tuple of (summary_text, summary_data_dict)
        """
        conversation_text = self._format_conversation(messages)
        
        prompt_parts = [
            "Please create a comprehensive summary of this Wisdom Agent session.",
            "\n\n=== CONVERSATION ===",
            conversation_text,
        ]
        
        if reflection_text:
            prompt_parts.extend([
                "\n\n=== SELF-REFLECTION ===",
                reflection_text,
            ])
        
        prompt_parts.extend([
            "\n\n=== SUMMARY REQUIREMENTS ===",
            "Create a structured summary with:",
            "",
            "1. **Major Themes** (2-4 themes)",
            "2. **Key Insights**",
            "   - User insights",
            "   - Wisdom Agent insights",
            "3. **Philosophical Developments**",
            "4. **Questions Raised**",
        ])
        
        if previous_summaries and len(previous_summaries) > 0:
            prompt_parts.extend([
                "",
                "5. **Connections to Previous Sessions**",
                "",
                "=== RECENT PREVIOUS SUMMARIES ===",
            ])
            for prev in previous_summaries[-5:]:
                prompt_parts.append(
                    f"\nSession {prev.get('session_id', 0):03d}: {prev.get('brief_synopsis', 'N/A')}"
                )
        
        prompt_parts.extend([
            "",
            "Be specific but concise (250-400 words total).",
            "",
            "Format:",
            "## Major Themes",
            "[Your response]",
            "",
            "## Key Insights",
            "**User:** [insights]",
            "**Wisdom Agent:** [insights]",
            "",
            "## Philosophical Developments",
            "[Your response]",
            "",
            "## Questions Raised",
            "[Your response]",
        ])
        
        if previous_summaries and len(previous_summaries) > 0:
            prompt_parts.extend([
                "",
                "## Connections to Previous Sessions",
                "[Your response with session references]",
            ])
        
        summary_prompt = "\n".join(prompt_parts)
        
        try:
            summary_text = self.llm_router.complete(
                messages=[{"role": "user", "content": summary_prompt}],
                system_prompt=f"You are the Wisdom Agent's summarization system.\n\n{self.philosophy_text}",
                max_tokens=2000,
                temperature=0.7
            )
            
            summary_data = self._parse_summary(summary_text, session_id)
            return summary_text, summary_data
            
        except Exception as e:
            fallback_text = f"Error generating summary: {e}\n\nSession {session_id:03d} completed."
            fallback_data = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'themes': [],
                'key_insights': {'user': [], 'wisdom_agent': []},
                'philosophical_developments': 'Error generating summary',
                'questions_raised': [],
                'connections_to_previous': {}
            }
            return fallback_text, fallback_data
    
    def generate_values_reflection(
        self,
        session_id: int,
        messages: List[Dict],
        rubric_text: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """
        Generate self-reflection using the 7 Universal Values rubric.
        
        This is the core self-evaluation that grounds the Wisdom Agent
        in Something Deeperism's values framework.
        
        Args:
            session_id: Session identifier
            messages: Conversation messages
            rubric_text: Optional custom rubric text
            
        Returns:
            Tuple of (reflection_text, scores_dict)
        """
        conversation_text = self._format_conversation(messages)
        
        # Load rubric if not provided
        if not rubric_text:
            rubric_path = config.PHILOSOPHY_BASE / "rubric.txt"
            if rubric_path.exists():
                with open(rubric_path, 'r') as f:
                    rubric_text = f.read()
            else:
                rubric_text = self._default_rubric()
        
        prompt = f"""Please evaluate your performance in this conversation using the 7 Universal Values rubric.

=== CONVERSATION ===
{conversation_text}

=== RUBRIC ===
{rubric_text}

=== YOUR TASK ===
Provide a detailed self-evaluation for each of the 7 Universal Values:

1. AWARENESS (0-10): Staying present to what's actually happening
2. HONESTY (0-10): Truth-telling even when difficult
3. ACCURACY (0-10): Precision in understanding and communication
4. COMPETENCE (0-10): Doing things well and skillfully
5. COMPASSION (0-10): Meeting all beings and their suffering with care
6. LOVING-KINDNESS (0-10): Active goodwill toward everyone
7. JOYFUL-SHARING (0-10): Generosity and celebration of the good

For EACH value:
- Give a score from 0-10
- Provide specific evidence from the conversation
- Note areas for improvement

End with an OVERALL REFLECTION on:
- How well you related responses to Pure Love and Reality
- Whether you maintained core commitments (no false certainty, never abandoning anyone)
- Patterns in strengths and weaknesses
- Specific changes for future conversations

Be genuinely self-critical but also acknowledge genuine strengths.
This is for learning, not self-flagellation."""

        try:
            response = self.llm_router.complete(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are performing honest self-evaluation as part of wisdom development.",
                max_tokens=3000,
                temperature=0.7
            )
            
            # Parse scores from response
            scores = self._extract_scores(response)
            
            # Format the reflection
            formatted = f"""{'=' * 70}
7 UNIVERSAL VALUES REFLECTION - Session {session_id:03d}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 70}

{response}

{'=' * 70}
SCORES SUMMARY:
{self._format_scores_summary(scores)}
{'=' * 70}
"""
            
            return formatted, scores
            
        except Exception as e:
            error_text = f"Error generating values reflection: {e}"
            empty_scores = {value: 0 for value in self.UNIVERSAL_VALUES}
            empty_scores['overall'] = 0
            return error_text, empty_scores
    
    def save_session_artifacts(
        self,
        session_id: int,
        messages: List[Dict],
        summary_text: str,
        summary_data: Dict,
        reflection_text: str,
        reflection_scores: Dict
    ) -> Dict[str, str]:
        """
        Save all session artifacts (conversation, summary, reflection).
        
        Args:
            session_id: Session identifier
            messages: Conversation messages
            summary_text: Generated summary text
            summary_data: Parsed summary data
            reflection_text: 7 Values reflection text
            reflection_scores: Parsed reflection scores
            
        Returns:
            Dictionary with paths to saved files
        """
        config.CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
        
        base_name = f"session_{session_id:03d}"
        saved_files = {}
        
        # Save conversation (text)
        conv_txt_path = config.CONVERSATIONS_DIR / f"{base_name}_conversation.txt"
        with open(conv_txt_path, 'w') as f:
            f.write(self._format_conversation(messages))
        saved_files['conversation_txt'] = str(conv_txt_path)
        
        # Save conversation (JSON)
        conv_json_path = config.CONVERSATIONS_DIR / f"{base_name}_conversation.json"
        with open(conv_json_path, 'w') as f:
            json.dump({
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'messages': messages
            }, f, indent=2)
        saved_files['conversation_json'] = str(conv_json_path)
        
        # Save summary (text)
        sum_txt_path = config.CONVERSATIONS_DIR / f"{base_name}_summary.txt"
        with open(sum_txt_path, 'w') as f:
            f.write(summary_text)
        saved_files['summary_txt'] = str(sum_txt_path)
        
        # Save summary (JSON)
        sum_json_path = config.CONVERSATIONS_DIR / f"{base_name}_summary.json"
        with open(sum_json_path, 'w') as f:
            json.dump(summary_data, f, indent=2)
        saved_files['summary_json'] = str(sum_json_path)
        
        # Save reflection (text)
        ref_txt_path = config.CONVERSATIONS_DIR / f"{base_name}_reflection.txt"
        with open(ref_txt_path, 'w') as f:
            f.write(reflection_text)
        saved_files['reflection_txt'] = str(ref_txt_path)
        
        # Save reflection (JSON)
        ref_json_path = config.CONVERSATIONS_DIR / f"{base_name}_reflection.json"
        with open(ref_json_path, 'w') as f:
            json.dump({
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'scores': reflection_scores,
                'reflection_text': reflection_text
            }, f, indent=2)
        saved_files['reflection_json'] = str(ref_json_path)
        
        return saved_files
    
    def update_meta_summary(
        self,
        session_id: int,
        session_summary: Dict
    ) -> Dict:
        """
        Update the evolving meta-summary with new session.
        
        The meta-summary tracks patterns, developments, and questions
        across all sessions - the evolving "memory" of wisdom development.
        
        Args:
            session_id: Session identifier
            session_summary: The session's summary data
            
        Returns:
            Updated meta-summary dictionary
        """
        # Load existing or create new
        meta = self.load_meta_summary() or {
            'created': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'total_sessions_synthesized': 0,
            'part_1_sequential': {},
            'part_2_thematic': {
                'key_patterns': [],
                'important_developments': [],
                'philosophical_evolution': [],
                'ongoing_questions': []
            }
        }
        
        # Update Part 1: Sequential summary
        brief = session_summary.get('brief_synopsis', f"Session {session_id:03d}")
        meta['part_1_sequential'][f'session_{session_id:03d}'] = brief
        
        # Update metadata
        meta['total_sessions_synthesized'] = session_id
        meta['last_updated'] = datetime.now().isoformat()
        
        # Update Part 2: Thematic sections using LLM
        meta = self._update_thematic_sections(meta, session_id, session_summary)
        
        # Save updated meta-summary
        with open(self.meta_summary_file, 'w') as f:
            json.dump(meta, f, indent=2)
        
        return meta
    
    def _update_thematic_sections(
        self,
        meta: Dict,
        session_id: int,
        session_summary: Dict
    ) -> Dict:
        """Use LLM to update thematic sections of meta-summary."""
        current_thematic = meta.get('part_2_thematic', {})
        
        prompt = f"""=== CURRENT THEMATIC SECTIONS ===
{json.dumps(current_thematic, indent=2)}

=== NEW SESSION SUMMARY (Session {session_id:03d}) ===
{json.dumps(session_summary, indent=2)}

=== YOUR TASK ===
Update the meta-summary's thematic sections:

1. **Key Patterns**: New or existing patterns?
2. **Important Developments**: Significant developments?
3. **Philosophical Evolution**: How did understanding evolve?
4. **Ongoing Questions**: New or revisited questions?

Respond in valid JSON:
{{
  "key_patterns": [
    {{
      "pattern": "Description",
      "sessions": [1, 3, {session_id}],
      "evolution": "How it evolved..."
    }}
  ],
  "important_developments": [
    {{
      "development": "What developed",
      "session": {session_id},
      "significance": "Why it matters"
    }}
  ],
  "philosophical_evolution": [
    {{
      "evolution": "What evolved",
      "session": {session_id},
      "connection_to_core": "Connection to philosophy"
    }}
  ],
  "ongoing_questions": [
    {{
      "question": "The question",
      "sessions": [{session_id}],
      "status": "Newly raised / Still exploring / Revisited"
    }}
  ]
}}

IMPORTANT: Return ONLY the JSON object."""

        try:
            response_text = self.llm_router.complete(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=f"You are the Wisdom Agent's meta-learning system.\n\n{self.philosophy_text}",
                max_tokens=3000,
                temperature=0.7
            )
            
            # Extract JSON
            response_text = self._extract_json(response_text)
            updated_thematic = json.loads(response_text)
            meta['part_2_thematic'] = updated_thematic
            
        except Exception as e:
            print(f"Warning: Could not update thematic sections: {e}")
        
        return meta
    
    def load_meta_summary(self) -> Optional[Dict]:
        """Load the current meta-summary."""
        if self.meta_summary_file.exists():
            with open(self.meta_summary_file, 'r') as f:
                return json.load(f)
        return None
    
    def format_meta_summary_for_prompt(self, meta: Optional[Dict] = None) -> str:
        """
        Format meta-summary for inclusion in system prompt.
        
        This provides the AI with context about the user's wisdom journey.
        
        Args:
            meta: Meta-summary dictionary (loads from file if not provided)
            
        Returns:
            Formatted string
        """
        if meta is None:
            meta = self.load_meta_summary()
            
        if not meta:
            return ""
        
        parts = [
            "\n" + "=" * 70,
            "YOUR EVOLVING WISDOM JOURNEY - META-SUMMARY",
            "=" * 70,
            ""
        ]
        
        # Part 1: Sequential (last 10 sessions)
        sequential = meta.get('part_1_sequential', {})
        if sequential:
            parts.append("Recent Sessions:")
            session_keys = sorted(sequential.keys())[-10:]
            for key in session_keys:
                session_num = key.replace('session_', '')
                parts.append(f"  • Session {session_num}: {sequential[key]}")
            parts.append("")
        
        # Part 2: Thematic
        thematic = meta.get('part_2_thematic', {})
        
        patterns = thematic.get('key_patterns', [])
        if patterns:
            parts.append("Key Patterns:")
            for p in patterns[-5:]:
                sessions = ', '.join(str(s) for s in p.get('sessions', []))
                parts.append(f"  • {p.get('pattern', 'N/A')} (Sessions: {sessions})")
            parts.append("")
        
        developments = thematic.get('important_developments', [])
        if developments:
            parts.append("Important Developments:")
            for d in developments[-5:]:
                parts.append(f"  • Session {d.get('session', 'N/A')}: {d.get('development', 'N/A')}")
            parts.append("")
        
        evolution = thematic.get('philosophical_evolution', [])
        if evolution:
            parts.append("Philosophical Evolution:")
            for e in evolution[-3:]:
                parts.append(f"  • Session {e.get('session', 'N/A')}: {e.get('evolution', 'N/A')}")
            parts.append("")
        
        questions = thematic.get('ongoing_questions', [])
        if questions:
            parts.append("Ongoing Questions:")
            for q in questions[-5:]:
                parts.append(f"  • {q.get('question', 'N/A')} ({q.get('status', 'N/A')})")
            parts.append("")
        
        parts.append("=" * 70)
        
        return "\n".join(parts)
    
    def get_recent_summaries(self, n: int = 5) -> List[Dict]:
        """
        Load the most recent session summaries.
        
        Args:
            n: Number of recent summaries
            
        Returns:
            List of summary dictionaries
        """
        summaries = []
        
        if not config.CONVERSATIONS_DIR.exists():
            return summaries
        
        summary_files = [
            f for f in os.listdir(config.CONVERSATIONS_DIR)
            if f.endswith('_summary.json')
        ]
        
        summary_files.sort(reverse=True)
        
        for filename in summary_files[:n]:
            filepath = config.CONVERSATIONS_DIR / filename
            try:
                with open(filepath, 'r') as f:
                    summaries.append(json.load(f))
            except Exception as e:
                print(f"Warning: Could not load {filename}: {e}")
        
        return summaries
    
    def get_values_trend(self, n_sessions: int = 10) -> Dict:
        """
        Analyze trends in 7 Values scores across recent sessions.
        
        Args:
            n_sessions: Number of sessions to analyze
            
        Returns:
            Dictionary with trend analysis
        """
        reflection_files = [
            f for f in os.listdir(config.CONVERSATIONS_DIR)
            if f.endswith('_reflection.json')
        ] if config.CONVERSATIONS_DIR.exists() else []
        
        reflection_files.sort(reverse=True)
        
        all_scores = []
        for filename in reflection_files[:n_sessions]:
            filepath = config.CONVERSATIONS_DIR / filename
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    all_scores.append(data.get('scores', {}))
            except Exception:
                continue
        
        if not all_scores:
            return {'message': 'No reflection data available'}
        
        # Calculate averages and trends
        trends = {}
        for value in self.UNIVERSAL_VALUES:
            scores = [s.get(value, 0) for s in all_scores if value in s]
            if scores:
                avg = sum(scores) / len(scores)
                # Simple trend: compare first half to second half
                mid = len(scores) // 2
                if mid > 0:
                    first_half = sum(scores[:mid]) / mid
                    second_half = sum(scores[mid:]) / (len(scores) - mid)
                    trend = "improving" if second_half > first_half else "declining" if second_half < first_half else "stable"
                else:
                    trend = "insufficient data"
                
                trends[value] = {
                    'average': round(avg, 2),
                    'trend': trend,
                    'recent': scores[0] if scores else 0
                }
        
        return {
            'sessions_analyzed': len(all_scores),
            'value_trends': trends
        }
    
    def _format_conversation(self, messages: List[Dict]) -> str:
        """Format conversation messages."""
        parts = []
        for msg in messages:
            role = msg.get('role', 'unknown').upper()
            content = msg.get('content', '')
            parts.append(f"{role}: {content}")
        return "\n\n".join(parts)
    
    def _parse_summary(self, summary_text: str, session_id: int) -> Dict:
        """Parse generated summary into structured data."""
        return {
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'summary_text': summary_text,
            'themes': self._extract_section(summary_text, "Major Themes"),
            'key_insights': {
                'user': self._extract_insights(summary_text, "User:"),
                'wisdom_agent': self._extract_insights(summary_text, "Wisdom Agent:")
            },
            'philosophical_developments': self._extract_section(summary_text, "Philosophical Developments"),
            'questions_raised': self._extract_section(summary_text, "Questions Raised"),
            'connections_to_previous': self._extract_section(summary_text, "Connections to Previous Sessions"),
            'brief_synopsis': summary_text[:200] + "..." if len(summary_text) > 200 else summary_text
        }
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a specific section from summary."""
        lines = text.split('\n')
        capturing = False
        section_lines = []
        
        for line in lines:
            if section_name.lower() in line.lower() and line.startswith('#'):
                capturing = True
                continue
            elif capturing and line.startswith('#'):
                break
            elif capturing:
                section_lines.append(line.strip())
        
        return '\n'.join(section_lines).strip()
    
    def _extract_insights(self, text: str, marker: str) -> List[str]:
        """Extract insights marked with User: or Wisdom Agent:"""
        lines = text.split('\n')
        insights = []
        
        for line in lines:
            if marker in line:
                insight = line.split(marker, 1)[1].strip()
                if insight:
                    insights.append(insight)
        
        return insights
    
    def _extract_scores(self, reflection_text: str) -> Dict:
        """Extract numerical scores from reflection text."""
        scores = {}
        
        for value in self.UNIVERSAL_VALUES:
            # Look for patterns like "AWARENESS (0-10): 8" or "Score: 8/10"
            import re
            patterns = [
                rf"{value}.*?(\d+)/10",
                rf"{value}.*?Score:\s*(\d+)",
                rf"{value}.*?:\s*(\d+)"
            ]
            
            for pattern in patterns:
                match = re.search(pattern, reflection_text, re.IGNORECASE)
                if match:
                    scores[value] = int(match.group(1))
                    break
            
            if value not in scores:
                scores[value] = 0
        
        # Calculate overall average
        if scores:
            scores['overall'] = round(sum(scores.values()) / len(scores), 2)
        
        return scores
    
    def _format_scores_summary(self, scores: Dict) -> str:
        """Format scores into readable summary."""
        lines = []
        for value in self.UNIVERSAL_VALUES:
            score = scores.get(value, 0)
            bar = "█" * score + "░" * (10 - score)
            lines.append(f"  {value:15} [{bar}] {score}/10")
        
        if 'overall' in scores:
            lines.append(f"\n  {'OVERALL':15} {scores['overall']:.1f}/10")
        
        return "\n".join(lines)
    
    def _extract_json(self, response: str) -> str:
        """Extract JSON from LLM response that may include markdown."""
        if "```json" in response:
            json_start = response.find("```json") + 7
            json_end = response.find("```", json_start)
            return response[json_start:json_end].strip()
        elif "```" in response:
            json_start = response.find("```") + 3
            json_end = response.find("```", json_start)
            return response[json_start:json_end].strip()
        return response
    
    def _default_rubric(self) -> str:
        """Return default rubric if file not found."""
        return """Evaluate your performance on each of the 7 Universal Values (0-10):
1. Awareness - Staying present to what's actually happening
2. Honesty - Truth-telling even when difficult
3. Accuracy - Precision in understanding and communication
4. Competence - Doing things well and skillfully
5. Compassion - Meeting all beings and their suffering with care
6. Loving-kindness - Active goodwill toward everyone
7. Joyful-sharing - Generosity and celebration of the good"""


def initialize_reflection_service(
    llm_router,
    philosophy_text: Optional[str] = None
) -> Optional[ReflectionService]:
    """
    Initialize and return a ReflectionService instance.
    
    Args:
        llm_router: LLMRouter instance (required)
        philosophy_text: Optional base philosophy text
        
    Returns:
        ReflectionService or None if initialization fails
    """
    global _reflection_service
    
    try:
        if not llm_router:
            raise ValueError("LLM Router required for Reflection Service")
        
        _reflection_service = ReflectionService(llm_router, philosophy_text)
        print("✓ Reflection Service initialized")
        return _reflection_service
        
    except Exception as e:
        print(f"Warning: Could not initialize ReflectionService: {e}")
        return None


def get_reflection_service() -> Optional[ReflectionService]:
    """Get the singleton ReflectionService instance."""
    return _reflection_service
