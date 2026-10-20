import os
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Safely patch PyAV 19.0+ built-in open() for faster-whisper compatibility
try:
    import av
    _orig_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception as _patch_err:
    pass

class BaseSpeechProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str | Path) -> Tuple[str, float]:
        """
        Transcribe an audio file.
        Returns: (transcript_text, confidence_score)
        """
        pass

class MockSpeechProvider(BaseSpeechProvider):
    def transcribe(self, audio_path: str | Path) -> Tuple[str, float]:
        return (
            "In our project, we implemented an asynchronous microservice architecture using FastAPI and PostgreSQL. "
            "We used connection pooling with SQLAlchemy to manage high concurrent loads, and offloaded heavy processing "
            "to background workers to ensure the primary HTTP event loop was never blocked.",
            0.96
        )

class FasterWhisperSpeechProvider(BaseSpeechProvider):
    def __init__(self, model_size: str | None = None):
        self.model_size = model_size or settings.WHISPER_MODEL_SIZE
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info(f"Loading faster-whisper model: {self.model_size} (CPU, int8)")
                self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            except Exception as e:
                logger.error(f"Failed to load faster-whisper: {e}. Falling back to Mock.")
                self._model = False
        return self._model

    def transcribe(self, audio_path: str | Path) -> Tuple[str, float]:
        model = self._get_model()
        if not model:
            return MockSpeechProvider().transcribe(audio_path)

        try:
            p = Path(audio_path)
            if p.exists() and p.suffix.lower() == ".webm":
                try:
                    raw_bytes = p.read_bytes()
                    ebml_idx = raw_bytes.find(b"\x1a\x45\xdf\xa3")
                    if ebml_idx > 0:
                        p.write_bytes(raw_bytes[ebml_idx:])
                except Exception as clean_err:
                    logger.debug(f"WebM EBML realignment notice: {clean_err}")

            initial_prompt = (
                "Technical software engineering interview. Topics: Python, JavaScript, TypeScript, "
                "FastAPI, Django, React, SQL, PostgreSQL, MongoDB, Docker, Kubernetes, AWS, "
                "Redis, microservices, async/await, concurrency, REST APIs, Git, CI/CD, algorithms, system design."
            )
            segments, info = model.transcribe(
                str(audio_path),
                beam_size=3,
                initial_prompt=initial_prompt,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400)
            )
            transcript_parts = []
            total_prob = 0.0
            count = 0

            for segment in segments:
                transcript_parts.append(segment.text.strip())
                # avg_logprob is log probability (e.g. -0.2 to -1.0)
                # Map to a 0.0 - 1.0 confidence estimate
                prob = min(max(1.0 + (segment.avg_logprob / 3.0), 0.1), 1.0)
                total_prob += prob
                count += 1

            full_transcript = " ".join(transcript_parts).strip()
            confidence = round(total_prob / count, 2) if count > 0 else 0.85
            return full_transcript, confidence
        except Exception as e:
            logger.error(f"faster-whisper transcription error: {e}. Returning empty fallback.")
            return "", 0.0

def get_speech_provider() -> BaseSpeechProvider:
    if settings.STT_PROVIDER == "faster-whisper":
        return FasterWhisperSpeechProvider()
    return MockSpeechProvider()
