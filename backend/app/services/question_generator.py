from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import Interview, InterviewQuestion, CandidateProfile
from backend.app.integrations import get_llm_provider

class QuestionGeneratorService:
    def __init__(self):
        self.llm = get_llm_provider()

    async def generate_interview_questions(
        self,
        db: Session,
        interview: Interview,
        profile: CandidateProfile | None
    ) -> List[InterviewQuestion]:
        """Generate structured questions based on candidate profile, target role, and track."""
        profile_data = {
            "full_name": profile.full_name if profile else "Candidate",
            "skills": profile.skills if profile else {},
            "projects": profile.projects if profile else [],
            "experience": profile.experience if profile else []
        }

        generated_raw = await self.llm.generate_questions(
            profile_data=profile_data,
            target_role=interview.target_role,
            interview_type=interview.interview_type,
            difficulty=interview.current_difficulty,
            count=interview.total_questions,
            assessed_topics=[],
            question_mix=getattr(interview, "question_mix", "mixed") or "mixed"
        )

        questions = []
        for idx, q_dict in enumerate(generated_raw, start=1):
            q_text = str(q_dict.get("question_text", "Explain your technical approach."))
            for old_c, new_c in [("\u2013", "-"), ("\u2014", "-"), ("\ufffd", "-"), ("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"')]:
                q_text = q_text.replace(old_c, new_c)

            q_type = str(q_dict.get("question_type", "SPOKEN")).upper().strip()
            if q_type not in ["SPOKEN", "MCQ", "CODE"]:
                q_type = "SPOKEN"

            question = InterviewQuestion(
                interview_id=interview.id,
                order_index=idx,
                question_text=q_text,
                skill_assessed=q_dict.get("skill_assessed", "System Design"),
                category=q_dict.get("category", "technical"),
                difficulty=interview.current_difficulty,
                expected_concepts=q_dict.get("expected_concepts", []),
                evaluation_rubric=q_dict.get("evaluation_rubric", {}),
                max_score=q_dict.get("max_score", 100.0),
                generation_source=q_dict.get("generation_source", "gemini"),
                question_type=q_type,
                options=q_dict.get("options", []),
                correct_option=q_dict.get("correct_option"),
                code_snippet=q_dict.get("code_snippet"),
                language=q_dict.get("language", "python"),
                explanation=q_dict.get("explanation"),
                examples=q_dict.get("examples", []),
                test_cases=q_dict.get("test_cases", []),
                constraints=q_dict.get("constraints", []),
                is_followup=False
            )
            db.add(question)
            questions.append(question)

        db.commit()
        for q in questions:
            db.refresh(q)
        return questions

    async def create_followup_question(
        self,
        db: Session,
        interview: Interview,
        parent_question: InterviewQuestion,
        candidate_transcript: str
    ) -> InterviewQuestion:
        """Create a targeted dynamic follow-up question digging into candidate's actual answer."""
        parent_data = {
            "question_text": parent_question.question_text,
            "skill_assessed": parent_question.skill_assessed,
            "difficulty": parent_question.difficulty
        }

        followup_data = await self.llm.generate_followup_question(parent_data, candidate_transcript)

        # Get highest current order index
        max_order = max([q.order_index for q in interview.questions], default=0)

        followup_q = InterviewQuestion(
            interview_id=interview.id,
            order_index=max_order + 1,
            question_text=followup_data.get("question_text"),
            skill_assessed=followup_data.get("skill_assessed", parent_question.skill_assessed),
            category="project_deep_dive",
            difficulty=interview.current_difficulty,
            expected_concepts=followup_data.get("expected_concepts", []),
            evaluation_rubric=followup_data.get("evaluation_rubric", {}),
            max_score=100.0,
            generation_source="dynamic_followup",
            parent_question_id=parent_question.id,
            is_followup=True
        )
        db.add(followup_q)
        interview.total_questions += 1
        db.commit()
        db.refresh(followup_q)
        return followup_q
