"""
Offline speech-to-text using faster-whisper.
Audio decoding uses PyAV (av package) which bundles its own ffmpeg —
no system-level ffmpeg installation required.
Model is loaded once at startup (singleton) and reused.
All transcription runs in a thread pool executor to avoid blocking the event loop.
"""
import asyncio
import io
import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

_model = None  # WhisperModel singleton

SAMPLE_RATE = 16000  # Whisper expects 16kHz audio


def get_model():
    """Return cached WhisperModel, loading it if not yet initialized."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        model_size = os.getenv("WHISPER_MODEL_SIZE", "small")
        logger.info("Loading Whisper model '%s'...", model_size)
        _model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("Whisper model '%s' loaded successfully", model_size)
    return _model


def preload_model() -> None:
    """Pre-load the Whisper model at startup to avoid cold start on first voice message."""
    try:
        get_model()
    except Exception as e:
        logger.warning("Whisper model preload failed: %s", e)


def _decode_ogg_to_numpy(ogg_bytes: bytes) -> np.ndarray:
    """
    Decode OGG/Opus audio bytes → float32 numpy array at 16kHz mono.
    Uses PyAV (av package) which bundles ffmpeg internally.
    No system ffmpeg required.
    """
    import av

    audio_chunks: list[np.ndarray] = []

    with av.open(io.BytesIO(ogg_bytes)) as container:
        resampler = av.AudioResampler(
            format="fltp",   # float32 planar
            layout="mono",
            rate=SAMPLE_RATE,
        )
        for frame in container.decode(audio=0):
            resampled_frames = resampler.resample(frame)
            # resample() may return a single frame or a list
            if resampled_frames is None:
                continue
            if not isinstance(resampled_frames, list):
                resampled_frames = [resampled_frames]
            for rf in resampled_frames:
                arr = rf.to_ndarray()  # shape: (1, N) for mono fltp
                audio_chunks.append(arr.flatten())

        # Flush resampler
        flushed = resampler.resample(None)
        if flushed is not None:
            flush_list = flushed if isinstance(flushed, list) else [flushed]
            for rf in flush_list:
                audio_chunks.append(rf.to_ndarray().flatten())

    if not audio_chunks:
        return np.array([], dtype=np.float32)

    return np.concatenate(audio_chunks).astype(np.float32)


def _sync_transcribe(ogg_bytes: bytes) -> str:
    """
    Synchronous transcription pipeline:
      OGG bytes → numpy float32 array (via PyAV) → faster-whisper → text
    Returns transcribed text or empty string on failure.
    """
    try:
        audio_array = _decode_ogg_to_numpy(ogg_bytes)

        if audio_array.size == 0:
            logger.warning("Decoded audio is empty")
            return ""

        duration_sec = audio_array.size / SAMPLE_RATE
        logger.debug("Decoded audio: %.1fs, %d samples", duration_sec, audio_array.size)

        model = get_model()
        segments, info = model.transcribe(
            audio_array,
            language="ru",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        logger.info("Transcribed %.1fs audio: '%s'", info.duration, text)
        return text

    except Exception as e:
        logger.error("Transcription error: %s", e, exc_info=True)
        return ""


async def transcribe_ogg(ogg_bytes: bytes) -> str:
    """
    Async wrapper: offloads transcription to thread pool so event loop stays responsive.
    Returns transcribed Russian text or empty string on failure.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_transcribe, ogg_bytes)
