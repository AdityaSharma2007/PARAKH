from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseLLMProvider(ABC):
    """Abstract interface for LLM services in PARAKH."""

    @abstractmethod
    async def extract_profile(self, raw_text: str) -> Dict[str, Any]:
        """Extract structured resume profile from raw text."""
        pass

    @abstractmethod
    async def generate_questions(
        self,
        profile_data: Dict[str, Any],
        target_role: str,
        interview_type: str,
        difficulty: str,
        count: int,
        assessed_topics: List[str],
        question_mix: str = "mixed"
    ) -> List[Dict[str, Any]]:
        """Generate tailored questions grounded in candidate projects and target role."""
        pass

    @abstractmethod
    async def generate_followup_question(
        self,
        previous_question: Dict[str, Any],
        candidate_transcript: str
    ) -> Dict[str, Any]:
        """Generate targeted follow-up question digging deeper into candidate's spoken response."""
        pass

    @abstractmethod
    async def evaluate_answer(
        self,
        question_data: Dict[str, Any],
        transcript: str,
        selected_option: str | None = None,
        code_submission: str | None = None
    ) -> Dict[str, Any]:
        """Evaluate spoken transcript, MCQ selection, or code solution against question rubric."""
        pass

    @abstractmethod
    async def check_knowledge_consistency(
        self,
        evaluations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analyze conceptual consistency across related questions."""
        pass
