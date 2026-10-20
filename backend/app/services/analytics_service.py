from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models.entities import Interview, AssessmentReport

class AnalyticsService:
    @staticmethod
    def get_candidate_progress(db: Session, candidate_id: int | None = None) -> Dict[str, Any]:
        """
        Computes multi-interview improvement metrics and progression trends.
        If candidate_id is None, aggregates across all completed interviews in the system.
        """
        query = db.query(Interview).join(AssessmentReport).order_by(Interview.created_at.asc())
        if candidate_id:
            query = query.filter(Interview.candidate_id == candidate_id)

        interviews = query.all()

        if not interviews:
            return {
                "total_interviews": 0,
                "average_score": 0.0,
                "highest_score": 0.0,
                "score_history": [],
                "skill_deltas": [],
                "reinforced_concepts": [],
                "persistent_gaps": []
            }

        score_history = []
        scores = []
        skill_history: Dict[str, List[float]] = {}

        for it in interviews:
            rep = it.report
            if not rep:
                continue
            scores.append(rep.overall_score)
            dt_str = it.created_at.strftime("%b %d, %Y") if it.created_at else "Recent"
            score_history.append({
                "interview_id": it.id,
                "date": dt_str,
                "target_role": it.target_role,
                "overall_score": rep.overall_score,
                "technical_score": rep.technical_score,
                "conceptual_score": rep.conceptual_score,
                "relevance_score": rep.relevance_score,
                "clarity_score": rep.clarity_score
            })

            # Track skills across reports
            for skill, sc in rep.competency_scores.items():
                if skill not in skill_history:
                    skill_history[skill] = []
                skill_history[skill].append(sc)

        skill_deltas = []
        for skill, sc_list in skill_history.items():
            first_sc = sc_list[0]
            latest_sc = sc_list[-1]
            delta = round(latest_sc - first_sc, 1)
            status = "IMPROVED" if delta > 5 else ("DECLINED" if delta < -5 else "STABLE")
            skill_deltas.append({
                "skill": skill,
                "first_score": first_sc,
                "latest_score": latest_sc,
                "delta": delta,
                "status": status
            })

        # Identify reinforced concepts (skills that moved from < 65 to >= 75)
        reinforced = [
            d["skill"] for d in skill_deltas
            if d["first_score"] < 65 and d["latest_score"] >= 75
        ]

        # Persistent gaps
        persistent = [
            d["skill"] for d in skill_deltas
            if d["latest_score"] < 65
        ]

        return {
            "total_interviews": len(interviews),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
            "highest_score": max(scores) if scores else 0.0,
            "score_history": score_history,
            "skill_deltas": skill_deltas,
            "reinforced_concepts": reinforced,
            "persistent_gaps": persistent
        }
