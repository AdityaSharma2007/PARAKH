import pytest
import numpy as np
import cv2
import base64
from backend.app.services.vision_analyzer import VisionAnalyzerService

def test_vision_analyzer_initialization():
    service = VisionAnalyzerService()
    assert service.is_opencv_ready is True
    assert service.face_cascade is not None

def test_vision_analyzer_frame_processing():
    service = VisionAnalyzerService()

    # Create a synthetic 320x240 image with a white circle (mock face)
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.circle(img, (160, 120), 50, (255, 255, 255), -1)

    _, buffer = cv2.imencode(".jpg", img)
    jpg_as_text = base64.b64encode(buffer).decode("utf-8")

    result = service.analyze_frame_data(jpg_as_text)

    # Result structure must have all required Computer Vision keys
    assert "face_detected" in result
    assert "eye_contact_ratio" in result
    assert "head_pose" in result
    assert "primary_emotion" in result
    assert "visual_confidence_score" in result

def test_vision_analyzer_report_generation():
    service = VisionAnalyzerService()
    
    # Test high performer visual telemetry
    high_report = service.generate_interview_vision_report(interview=None, average_score=85.0)
    assert high_report["visual_confidence_score"] >= 75.0
    assert high_report["stress_indicator_level"] == "LOW"
    assert "computer_vision_methodology" in high_report
    assert "face_detection_model" in high_report["computer_vision_methodology"]
    assert "eye_tracking_method" in high_report["computer_vision_methodology"]

    # Test struggling candidate visual telemetry (score < 40)
    low_report = service.generate_interview_vision_report(interview=None, average_score=25.0)
    assert low_report["visual_confidence_score"] <= 65.0
    assert low_report["stress_indicator_level"] == "ELEVATED"
    assert low_report["emotion_distribution"]["hesitant"] > 20.0
