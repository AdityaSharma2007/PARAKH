from typing import List
from sqlalchemy.orm import Session
from backend.app.models.entities import Interview, KnowledgeConsistencyCheck
from backend.app.integrations import get_llm_provider

class ConsistencyEngine:
    def __init__(self):
        self.llm = get_llm_provider()

    async def analyze_consistency(self, db: Session, interview: Interview) -> List[KnowledgeConsistencyCheck]:
        evaluations_payload = []
        for q in interview.questions:
            if q.answer and q.answer.evaluation:
                ev = q.answer.evaluation
                evaluations_payload.append({
                    "question_id": q.id,
                    "skill_assessed": q.skill_assessed,
                    "overall_score": ev.overall_score,
                    "technical_score": ev.technical_score,
                    "conceptual_score": ev.conceptual_score,
                    "correct_concepts": ev.correct_concepts,
                    "missing_concepts": ev.missing_concepts
                })

        if len(evaluations_payload) < 2:
            return []

        results = await self.llm.check_knowledge_consistency(evaluations_payload)

        # Clear prior checks for this interview
        db.query(KnowledgeConsistencyCheck).filter_by(interview_id=interview.id).delete()

        checks = []
        for r in results:
            check = KnowledgeConsistencyCheck(
                interview_id=interview.id,
                concept_area=r.get("concept_area", "General Engineering"),
                questions_compared=r.get("questions_compared", []),
                consistency_score=r.get("consistency_score", 0.85),
                discrepancy_details=r.get("discrepancy_details", "No major discrepancies found."),
                root_cause=r.get("root_cause", "Consistent technical foundation")
            )
            db.add(check)
            checks.append(check)

        db.commit()
        return checks
