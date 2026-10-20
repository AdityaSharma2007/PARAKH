from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import Interview, EvidenceNode, VerificationStatus

class EvidenceGraphService:
    @staticmethod
    def sync_evidence_nodes(db: Session, interview: Interview) -> List[EvidenceNode]:
        """
        Builds and updates the Resume-to-Evidence Intelligence Graph.
        Maps skills and project claims from the candidate profile to interview answers and evaluations.
        """
        profile = interview.resume.profile if interview.resume else None
        if not profile:
            return []

        # Existing nodes for this interview
        existing_nodes = {n.claim_text.lower(): n for n in interview.evidence_nodes}

        # Collect claims from skills and projects
        skills_flat = []
        if isinstance(profile.skills, dict):
            for items in profile.skills.values():
                if isinstance(items, list):
                    skills_flat.extend(items)
        elif isinstance(profile.skills, list):
            skills_flat.extend(profile.skills)

        # Collect question-evaluation map
        eval_map = {}
        for q in interview.questions:
            if q.answer and q.answer.evaluation:
                eval_map[q.skill_assessed.lower()] = (q, q.answer, q.answer.evaluation)

        updated_nodes = []

        # Process skill claims
        for skill in set(skills_flat):
            skill_key = skill.lower()
            matching_eval = None
            for s_key, data in eval_map.items():
                if skill_key in s_key or s_key in skill_key:
                    matching_eval = data
                    break

            status = VerificationStatus.UNVERIFIED.value
            confidence = 0.0
            evidence_quote = None
            q_id = None

            if matching_eval:
                q, ans, ev = matching_eval
                q_id = q.id
                confidence = ev.overall_score
                if ev.overall_score >= 75.0:
                    status = VerificationStatus.VERIFIED.value
                elif ev.overall_score >= 50.0:
                    status = VerificationStatus.PARTIALLY_DEMONSTRATED.value
                else:
                    status = VerificationStatus.CONTRADICTORY.value

                if ev.transcript_evidence:
                    evidence_quote = ev.transcript_evidence[0] if isinstance(ev.transcript_evidence, list) else str(ev.transcript_evidence)

            if skill_key in existing_nodes:
                node = existing_nodes[skill_key]
                node.verified_status = status
                node.confidence_score = confidence
                node.evidence_quote = evidence_quote
                node.related_question_id = q_id
            else:
                node = EvidenceNode(
                    candidate_id=interview.candidate_id,
                    interview_id=interview.id,
                    claim_type="skill",
                    claim_text=skill,
                    verified_status=status,
                    confidence_score=confidence,
                    evidence_quote=evidence_quote,
                    related_question_id=q_id
                )
                db.add(node)
            updated_nodes.append(node)

        # Process project claims
        for proj in profile.projects:
            if isinstance(proj, dict) and "title" in proj:
                p_title = proj["title"]
                p_key = p_title.lower()
                matching_proj_eval = None
                for s_key, data in eval_map.items():
                    if "architecture" in s_key or "project" in s_key or p_key in s_key:
                        matching_proj_eval = data
                        break

                p_status = VerificationStatus.UNVERIFIED.value
                p_conf = 0.0
                p_quote = None
                p_qid = None

                if matching_proj_eval:
                    q, ans, ev = matching_proj_eval
                    p_qid = q.id
                    p_conf = ev.overall_score
                    if ev.overall_score >= 70.0:
                        p_status = VerificationStatus.VERIFIED.value
                    elif ev.overall_score >= 45.0:
                        p_status = VerificationStatus.PARTIALLY_DEMONSTRATED.value
                    else:
                        p_status = VerificationStatus.CONTRADICTORY.value
                    if ev.transcript_evidence:
                        p_quote = ev.transcript_evidence[0] if isinstance(ev.transcript_evidence, list) else str(ev.transcript_evidence)

                if p_key in existing_nodes:
                    node = existing_nodes[p_key]
                    node.verified_status = p_status
                    node.confidence_score = p_conf
                    node.evidence_quote = p_quote
                    node.related_question_id = p_qid
                else:
                    node = EvidenceNode(
                        candidate_id=interview.candidate_id,
                        interview_id=interview.id,
                        claim_type="project_claim",
                        claim_text=p_title,
                        verified_status=p_status,
                        confidence_score=p_conf,
                        evidence_quote=p_quote,
                        related_question_id=p_qid
                    )
                    db.add(node)
                updated_nodes.append(node)

        db.commit()
        return updated_nodes
