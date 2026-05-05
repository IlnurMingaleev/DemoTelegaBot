---
name: faster-whisper-stt
description: Offline speech-to-text using faster-whisper (free, no API key). Use when implementing voice message transcription in the Telegram bot. Covers model loading singleton, .ogg to .wav conversion via pydub, async transcription offloaded to thread pool.
disable-model-invocation: true
---

# faster-whisper STT

## Installation

```
faster-whisper>=1.0.0
pydub>=0.25.1
```

System requirement: **ffmpeg** must be installed and on PATH.
- Windows: `winget install ffmpeg` or download from ffmpeg.org
- Linux: `apt install ffmpeg`

## Model loading (singleton — load once at startup)

```python
from faster_whisper import WhisperModel

_model: WhisperModel | None = None

def get_model() -> WhisperModel:
    global _model
    if _model is None:
        # model_size: "tiny" (fast) | "small" (balanced) | "medium" (accurate)
        # Use "small" for Russian — good accuracy, runs on CPU ~2-4s per 30s audio
        _model = WhisperModel("small", device="cpu", compute_type="int8")
    return _model
```

Call `get_model()` at bot startup (`on_startup`) to avoid cold start on first voice message.

## .ogg → transcription pipeline

```python
import asyncio
import tempfile
from pathlib import Path
from pydub import AudioSegment

async def transcribe_ogg(ogg_path: str) -> str:
    """Convert .ogg voice to text. Returns empty string on failure."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_transcribe, ogg_path)

def _sync_transcribe(ogg_path: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    try:
        audio = AudioSegment.from_ogg(ogg_path)
        audio.export(wav_path, format="wav")
        model = get_model()
        segments, info = model.transcribe(wav_path, language="ru", beam_size=5)
        return " ".join(seg.text.strip() for seg in segments)
    finally:
        Path(wav_path).unlink(missing_ok=True)
```

## Downloading voice from Telegram

```python
async def download_voice(bot: Bot, voice: types.Voice, dest: str) -> None:
    file = await bot.get_file(voice.file_id)
    await bot.download_file(file.file_path, dest)
```

## Full handler pattern

```python
import tempfile, os
from aiogram import types, Bot

@dp.message(F.voice)
async def handle_voice(message: types.Message, bot: Bot) -> None:
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        ogg_path = f.name
    try:
        await download_voice(bot, message.voice, ogg_path)
        text = await transcribe_ogg(ogg_path)
        if not text:
            await message.answer("❌ Не удалось распознать голос. Попробуйте ещё раз.")
            return
        # pass `text` to NLP service
    finally:
        os.unlink(ogg_path)
```

## Model size trade-offs

| Model  | Size   | CPU speed (30s audio) | Russian accuracy |
|--------|--------|-----------------------|-----------------|
| tiny   | ~75MB  | ~0.5s                 | Acceptable      |
| small  | ~244MB | ~2s                   | Good ✅          |
| medium | ~769MB | ~8s                   | Best            |

Use `small` as default. User can override via `WHISPER_MODEL_SIZE` env var.

## Common issues

- `ffmpeg not found`: install ffmpeg and restart terminal
- Slow first transcription: model loading (~3s) — call `get_model()` on startup
- Empty transcript: audio too short (<0.5s) or silence — check `info.duration`
