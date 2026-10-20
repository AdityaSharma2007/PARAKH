from fastapi import APIRouter, Depends, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import Dict, Any
from backend.app.db.database import get_db
from backend.app.core.exceptions import EntityNotFoundError
from backend.app.models.entities import Interview
from backend.app.services.vision_analyzer import VisionAnalyzerService

router = APIRouter(prefix="/interviews/{interview_id}/vision", tags=["Computer Vision Analytics"])
vision_service = VisionAnalyzerService()

@router.post("/frame")
async def analyze_camera_frame(
    interview_id: int,
    image_base64: str | None = Form(None),
    frame_file: UploadFile | None = File(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Receives a live webcam video frame and returns real-time Computer Vision telemetry:
    Face bounding box, eye contact ratio, head pose, facial emotion, and visual confidence.
    """
    interview = db.query(Interview).filter_by(id=interview_id).first()
    if not interview:
        raise EntityNotFoundError("Interview", interview_id)

    raw_data = None
    if frame_file and frame_file.filename:
        raw_data = await frame_file.read()
    elif image_base64:
        raw_data = image_base64

    if not raw_data:
        return vision_service._get_fallback_frame_result(face_detected=False)

    return vision_service.analyze_frame_data(raw_data, interview_id=interview_id)

@router.get("/analytics")
def get_interview_vision_analytics(interview_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns full Computer Vision analytics for an interview session.
    """
    interview = db.query(Interview).filter_by(id=interview_id).first()
    if not interview:
        raise EntityNotFoundError("Interview", interview_id)

    if interview.report and interview.report.vision_analytics:
        return interview.report.vision_analytics

    avg_score = interview.report.overall_score if interview.report else 70.0
    return VisionAnalyzerService.generate_interview_vision_report(interview, average_score=avg_score)
