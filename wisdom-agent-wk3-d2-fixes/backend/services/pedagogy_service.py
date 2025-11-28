"""
Wisdom Agent - Pedagogy Service

Manages educational conversations, generates pedagogical reflections,
tracks learning progress, and generates adaptive learning plans.

Migrated from pedagogy_manager.py with new config system integration.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any

from backend.config import config


# Singleton instance
_pedagogy_service: Optional['PedagogyService'] = None


class PedagogyService:
    """Manages pedagogical aspects of learning sessions."""
    
    def __init__(self, llm_router):
        """
        Initialize Pedagogy Service.
        
        Args:
            llm_router: LLMRouter instance for generating reflections
        """
        self.llm_router = llm_router
    
    def generate_learning_plan(
        self,
        subject: str,
        current_level: str,
        learning_goal: str,
        time_commitment: str,
        preferred_style: Optional[str] = None
    ) -> Dict:
        """
        Generate a personalized learning plan.
        
        Args:
            subject: What to learn (e.g., "Linear Algebra")
            current_level: Current knowledge level
            learning_goal: What they want to achieve
            time_commitment: How much time they can dedicate
            preferred_style: Learning style preferences
            
        Returns:
            Dictionary with structured learning plan
        """
        prompt = f"""Create a personalized learning plan for a student.

SUBJECT: {subject}

CURRENT LEVEL: {current_level}

LEARNING GOAL: {learning_goal}

TIME COMMITMENT: {time_commitment}

PREFERRED STYLE: {preferred_style or "Not specified"}

Please create a structured learning plan that includes:
1. **Assessment of Starting Point**: Where they are now
2. **Milestones**: 5-7 key milestones toward the goal
3. **Learning Path**: Recommended sequence of topics
4. **Resources**: Suggested books, videos, practice problems
5. **Timeline**: Realistic timeline based on time commitment
6. **First Session**: What we should start with today

Be realistic, encouraging, and adaptive. Emphasize that plans evolve based on actual learning.

Respond in JSON format:
{{
  "assessment": "...",
  "milestones": [
    {{"name": "...", "description": "...", "estimated_time": "..."}},
    ...
  ],
  "learning_path": ["Topic 1", "Topic 2", ...],
  "resources": [
    {{"type": "...", "title": "...", "url": "..."}},
    ...
  ],
  "timeline": "...",
  "first_session_focus": "..."
}}

IMPORTANT: Return ONLY valid JSON, no other text."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_router.complete(
                messages=messages,
                system_prompt="You are an expert educator creating personalized learning plans.",
                temperature=0.7
            )
            
            # Extract JSON from response
            response = self._extract_json(response)
            plan = json.loads(response)
            plan['created'] = datetime.now().isoformat()
            plan['subject'] = subject
            
            return plan
            
        except Exception as e:
            print(f"Error generating learning plan: {e}")
            # Return basic fallback plan
            return {
                'subject': subject,
                'assessment': f"Ready to learn {subject}",
                'milestones': [],
                'learning_path': [],
                'resources': [],
                'timeline': "To be determined",
                'first_session_focus': f"Introduction to {subject}",
                'created': datetime.now().isoformat()
            }
    
    def generate_pedagogical_reflection(
        self,
        session_id: int,
        messages: List[Dict],
        project_context: Optional[Dict] = None
    ) -> str:
        """
        Generate pedagogical reflection on a learning session.
        
        This focuses on teaching effectiveness, learning progress,
        and recommendations for future sessions.
        
        Args:
            session_id: Session identifier
            messages: Conversation messages
            project_context: Optional project context (learning plan, progress)
            
        Returns:
            Pedagogical reflection text
        """
        # Build conversation text
        conversation_text = self._format_conversation(messages)
        
        # Build context
        context_parts = []
        if project_context:
            if project_context.get('learning_plan'):
                context_parts.append(f"Learning Goal: {project_context['learning_plan'].get('goal', 'N/A')}")
            if project_context.get('progress'):
                context_parts.append(f"Current Progress: {project_context['progress']}")
        
        context = "\n".join(context_parts) if context_parts else "No prior context"
        
        prompt = f"""Please reflect on this learning session from a pedagogical perspective.

=== CONTEXT ===
{context}

=== CONVERSATION ===
{conversation_text}

=== REFLECTION REQUIREMENTS ===

Provide a structured pedagogical reflection with these sections:

1. **WHAT WAS LEARNED**
   - Key concepts the student grasped
   - Skills practiced
   - Connections made to prior knowledge

2. **CURRENT UNDERSTANDING**
   - Topics where understanding seems solid
   - Topics where understanding is developing
   - Gaps or misconceptions identified

3. **PEDAGOGICAL EFFECTIVENESS**
   - What teaching approaches worked well
   - What didn't work (if anything)
   - Student engagement level
   - Pacing assessment

4. **NEXT SESSION PLAN**
   - Topics that need review
   - New material to introduce
   - Exercises or practice to recommend
   - Questions to explore

5. **LONG-TERM PROGRESS**
   - Trajectory (on track, ahead, needs adjustment)
   - Changes to learning plan (if any)
   - Milestones reached
   - Celebration of growth

IMPORTANT: 
- Be honest about gaps without discouragement
- Celebrate genuine progress
- Be specific with examples
- Provide actionable next steps
- If this was a shared contemplation rather than one-way teaching, note that
- Remember: wisdom sessions are collaborative journeys, not hierarchical teaching

Format your response as clear, readable text (not a list of bullet points)."""

        try:
            reflection_messages = [{"role": "user", "content": prompt}]
            
            reflection = self.llm_router.complete(
                messages=reflection_messages,
                system_prompt="You are reflecting on a learning session to guide future pedagogy.",
                temperature=0.7
            )
            
            # Format for storage
            formatted = f"""{'=' * 70}
PEDAGOGICAL REFLECTION - Session {session_id:03d}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 70}

{reflection}

{'=' * 70}
"""
            
            return formatted
            
        except Exception as e:
            return f"Error generating pedagogical reflection: {e}"
    
    def detect_session_type(self, messages: List[Dict]) -> str:
        """
        Detect the type of session based on conversation content.
        
        Args:
            messages: Conversation messages
            
        Returns:
            Session type (wisdom_only, learning_only, mixed, fact_checking, etc.)
        """
        # Simple heuristic detection
        conversation_text = " ".join([msg.get('content', '') for msg in messages]).lower()
        
        # Keywords for different session types
        learning_keywords = ['explain', 'how does', 'what is', 'teach', 'learn', 'understand', 
                            'practice', 'exercise', 'homework', 'study']
        wisdom_keywords = ['wisdom', 'meaning', 'purpose', 'values', 'should i', 'ethical',
                          'moral', 'philosophy', 'contemplat']
        fact_check_keywords = ['fact check', 'is this true', 'verify', 'claim', 'evidence']
        
        learning_count = sum(1 for kw in learning_keywords if kw in conversation_text)
        wisdom_count = sum(1 for kw in wisdom_keywords if kw in conversation_text)
        fact_check_count = sum(1 for kw in fact_check_keywords if kw in conversation_text)
        
        # Determine type
        if fact_check_count > 2:
            return "fact_checking"
        elif learning_count > wisdom_count and learning_count > 3:
            return "learning_only"
        elif wisdom_count > learning_count and wisdom_count > 3:
            return "wisdom_only"
        elif learning_count > 0 and wisdom_count > 0:
            return "mixed"
        else:
            # Look for collaborative language
            if any(word in conversation_text for word in ['together', 'both', 'shared', 'mutual']):
                return "shared_contemplation"
            return "wisdom_only"  # Default
    
    def generate_progress_update(
        self,
        project_context: Dict,
        recent_sessions: List[Dict]
    ) -> Dict:
        """
        Generate progress update for a learning project.
        
        Args:
            project_context: Project context (learning plan, current progress)
            recent_sessions: Recent session summaries
            
        Returns:
            Dictionary with progress assessment
        """
        # Build summary of recent activity
        activity_summary = []
        for session in recent_sessions:
            activity_summary.append(f"Session {session.get('session_id')}: {session.get('summary', 'N/A')}")
        
        prompt = f"""Assess learning progress for this project.

=== LEARNING PLAN ===
{json.dumps(project_context.get('learning_plan', {}), indent=2)}

=== CURRENT PROGRESS ===
{json.dumps(project_context.get('progress', {}), indent=2)}

=== RECENT SESSIONS ===
{chr(10).join(activity_summary) if activity_summary else "No recent sessions"}

=== ASSESSMENT REQUEST ===

Provide a progress update with:
1. **Overall Status**: On track / Ahead / Behind / Needs adjustment
2. **Milestones Reached**: Which milestones have been achieved
3. **Current Strengths**: What's going well
4. **Areas for Focus**: What needs more attention
5. **Recommended Adjustments**: Any changes to learning plan
6. **Encouragement**: Genuine celebration of progress

Respond in JSON format:
{{
  "status": "...",
  "milestones_reached": ["...", "..."],
  "strengths": ["...", "..."],
  "focus_areas": ["...", "..."],
  "adjustments": ["...", "..."],
  "encouragement": "..."
}}

Return ONLY valid JSON."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_router.complete(
                messages=messages,
                system_prompt="You are assessing student progress with wisdom and encouragement.",
                temperature=0.7
            )
            
            # Extract JSON
            response = self._extract_json(response)
            progress = json.loads(response)
            progress['generated'] = datetime.now().isoformat()
            
            return progress
            
        except Exception as e:
            print(f"Error generating progress update: {e}")
            return {
                'status': 'In Progress',
                'milestones_reached': [],
                'strengths': [],
                'focus_areas': [],
                'adjustments': [],
                'encouragement': 'Keep learning!',
                'generated': datetime.now().isoformat()
            }
    
    def suggest_next_topics(
        self,
        learning_plan: Dict,
        completed_topics: List[str],
        recent_performance: Optional[Dict] = None
    ) -> Dict:
        """
        Suggest next topics based on learning progress.
        
        Args:
            learning_plan: The original learning plan
            completed_topics: Topics already covered
            recent_performance: Optional performance data
            
        Returns:
            Dictionary with suggested next topics and rationale
        """
        prompt = f"""Based on the learning plan and progress, suggest the next topics to study.

=== LEARNING PLAN ===
{json.dumps(learning_plan, indent=2)}

=== COMPLETED TOPICS ===
{json.dumps(completed_topics, indent=2)}

=== RECENT PERFORMANCE ===
{json.dumps(recent_performance, indent=2) if recent_performance else "No performance data"}

=== YOUR TASK ===
Suggest 2-3 topics that should be studied next, considering:
- The logical progression of the subject
- Prerequisites for upcoming topics
- Areas that may need reinforcement
- The student's apparent interests

Respond in JSON format:
{{
  "next_topics": [
    {{"topic": "...", "rationale": "...", "priority": "high/medium/low"}},
    ...
  ],
  "review_needed": ["topic1", "topic2"],
  "estimated_sessions": 3
}}

Return ONLY valid JSON."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = self.llm_router.complete(
                messages=messages,
                system_prompt="You are an expert educator planning the next learning steps.",
                temperature=0.7
            )
            
            response = self._extract_json(response)
            return json.loads(response)
            
        except Exception as e:
            print(f"Error suggesting next topics: {e}")
            return {
                'next_topics': [],
                'review_needed': [],
                'estimated_sessions': 1
            }
    
    def _format_conversation(self, messages: List[Dict]) -> str:
        """Format conversation messages for analysis."""
        parts = []
        for msg in messages:
            role = msg.get('role', 'unknown').upper()
            content = msg.get('content', '')
            parts.append(f"{role}: {content}")
        return "\n\n".join(parts)
    
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


def initialize_pedagogy_service(llm_router) -> Optional[PedagogyService]:
    """
    Initialize and return a PedagogyService instance.
    
    Args:
        llm_router: LLMRouter instance (required)
        
    Returns:
        PedagogyService or None if initialization fails
    """
    global _pedagogy_service
    
    try:
        if not llm_router:
            raise ValueError("LLM Router required for Pedagogy Service")
        
        _pedagogy_service = PedagogyService(llm_router)
        print("✓ Pedagogy Service initialized")
        return _pedagogy_service
        
    except Exception as e:
        print(f"Warning: Could not initialize PedagogyService: {e}")
        return None


def get_pedagogy_service() -> Optional[PedagogyService]:
    """Get the singleton PedagogyService instance."""
    return _pedagogy_service
