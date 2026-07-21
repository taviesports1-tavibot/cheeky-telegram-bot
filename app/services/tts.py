from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import edge_tts
import structlog

log = structlog.get_logger()

ALLOWED_VOICES = {
    "ru-RU-DmitryNeural",
    "ru-RU-SvetlanaNeural",
    "uk-UA-OstapNeural",
    "de-DE-ConradNeural",
    "en-US-GuyNeural",
}


class TTSService:
    def __init__(self, default_voice: str, max_length: int = 1000) -> None:
        self.default_voice = (
            default_voice if default_voice in ALLOWED_VOICES else "ru-RU-DmitryNeural"
        )
        self.max_length = max_length

    async def synthesize(self, text: str, voice: str | None = None) -> Path | None:
        clean = text.strip()[: self.max_length]
        if not clean:
            return None
        selected = voice if voice in ALLOWED_VOICES else self.default_voice
        temp_dir = Path(tempfile.mkdtemp(prefix="cheeky_tts_"))
        mp3 = temp_dir / "speech.mp3"
        ogg = temp_dir / "speech.ogg"
        try:
            await edge_tts.Communicate(clean, selected).save(str(mp3))
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(mp3),
                "-c:a",
                "libopus",
                "-b:a",
                "48k",
                str(ogg),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode != 0:
                log.error("tts_ffmpeg_failed", error=stderr.decode(errors="replace")[:300])
                await self.cleanup(mp3)
                return None
            mp3.unlink(missing_ok=True)
            return ogg
        except Exception as exc:
            log.error("tts_failed", error=type(exc).__name__)
            await self.cleanup(mp3)
            return None

    async def cleanup(self, path: Path | None) -> None:
        if path is None:
            return
        await asyncio.to_thread(self._remove_temporary, path)

    @staticmethod
    def _remove_temporary(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
            path.parent.rmdir()
        except OSError:
            pass
