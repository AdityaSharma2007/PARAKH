from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.core.exceptions import EntityNotFoundError
from backend.app.models.entities import Interview, AssessmentReport, EvidenceNode, KnowledgeConsistencyCheck
from backend.app.schemas.evaluation import AssessmentReportResponse, EvidenceNodeResponse
from backend.app.services.scoring_engine import ScoringEngine

router = APIRouter(tags=["Reports & Assessments"])

@router.get("/interviews/{interview_id}/report", response_model=AssessmentReportResponse)
async def get_interview_report(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(id=interview_id).first()
    if not interview:
        raise EntityNotFoundError("Interview", interview_id)

    report = interview.report
    if not report:
        # Generate report if not yet generated
        report = await ScoringEngine.generate_final_report(db, interview)
    elif not report.vision_analytics:
        from backend.app.services.vision_analyzer import VisionAnalyzerService
        report.vision_analytics = VisionAnalyzerService.generate_interview_vision_report(interview, average_score=report.overall_score)
        db.commit()
        db.refresh(report)

    # Collect evaluations
    evaluations = []
    for q in interview.questions:
        if q.answer and q.answer.evaluation:
            evaluations.append(q.answer.evaluation)

    # Collect evidence nodes
    evidence_nodes = db.query(EvidenceNode).filter_by(interview_id=interview.id).all()

    return AssessmentReportResponse(
        id=report.id,
        interview_id=interview.id,
        overall_score=report.overall_score,
        technical_score=report.technical_score,
        conceptual_score=report.conceptual_score,
        relevance_score=report.relevance_score,
        clarity_score=report.clarity_score,
        competency_scores=report.competency_scores or {},
        strengths=report.strengths or [],
        areas_for_improvement=report.areas_for_improvement or [],
        recommendations=report.recommendations or [],
        knowledge_gap_map=report.knowledge_gap_map or {},
        completion_stats=report.completion_stats or {},
        vision_analytics=report.vision_analytics or {},
        audio_analytics=report.audio_analytics or {},
        evaluations=evaluations,
        evidence_nodes=evidence_nodes,
        generated_at=report.generated_at
    )

@router.get("/interviews/{interview_id}/evidence-graph")
def get_interview_evidence_graph(interview_id: int, db: Session = Depends(get_db)):
    nodes = db.query(EvidenceNode).filter_by(interview_id=interview_id).all()
    return {
        "interview_id": interview_id,
        "nodes": [
            {
                "id": n.id,
                "claim_type": n.claim_type,
                "claim_text": n.claim_text,
                "verified_status": n.verified_status,
                "confidence_score": n.confidence_score,
                "evidence_quote": n.evidence_quote,
                "related_question_id": n.related_question_id
            }
            for n in nodes
        ]
    }

@router.get("/interviews/{interview_id}/consistency")
def get_interview_consistency(interview_id: int, db: Session = Depends(get_db)):
    checks = db.query(KnowledgeConsistencyCheck).filter_by(interview_id=interview_id).all()
    return {
        "interview_id": interview_id,
        "consistency_checks": [
            {
                "id": c.id,
                "concept_area": c.concept_area,
                "questions_compared": c.questions_compared,
                "consistency_score": c.consistency_score,
                "discrepancy_details": c.discrepancy_details,
                "root_cause": c.root_cause
            }
            for c in checks
        ]
    }
