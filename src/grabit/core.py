"""Thin, testable wrapper around yt-dlp.

yt-dlp does the hard work of supporting hundreds of sites; grabit only
decides *what* to download and reports progress in a stable shape.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadError, YoutubeDLError

AUDIO_FORMATS = ("mp3", "m4a", "flac", "wav", "opus")


class GrabitError(Exception):
    """A problem grabit can explain to the user."""


@dataclass
class GrabOptions:
    url: str
    output_dir: Path = Path("~/Downloads")
    audio_only: bool = False
    audio_format: str = "mp3"
    max_height: int | None = None
    filename_template: str = "%(title).200B [%(id)s].%(ext)s"
    cookies_from_browser: str | None = None
    subtitles: bool = False
    playlist: bool = False

    def __post_init__(self) -> None:
        if self.audio_format not in AUDIO_FORMATS:
            raise GrabitError(
                f"Unsupported audio format '{self.audio_format}'. "
                f"Choose one of: {', '.join(AUDIO_FORMATS)}."
            )
        if self.max_height is not None and self.max_height <= 0:
            raise GrabitError("--max-height must be a positive number.")
        self.output_dir = Path(self.output_dir).expanduser()


@dataclass
class GrabResult:
    title: str
    filepath: Path
    extractor: str
    duration: float | None
    filesize: int | None


@dataclass
class Progress:
    """Latest progress snapshot, in bytes and seconds."""

    status: str = "starting"
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    speed: float | None = None
    eta: float | None = None
    filename: str | None = None

    @property
    def percent(self) -> float | None:
        if not self.total_bytes:
            return None
        return self.downloaded_bytes / self.total_bytes * 100


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def build_ydl_opts(options: GrabOptions) -> dict:
    """Translate grabit options into yt-dlp options."""
    if options.audio_only:
        fmt = "bestaudio/best"
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": options.audio_format,
                "preferredquality": "0",
            }
        ]
    else:
        height = f"[height<={options.max_height}]" if options.max_height else ""
        # Prefer a single stream that already contains audio; fall back to
        # merging the best video and audio tracks.
        fmt = (
            f"bestvideo{height}[vcodec!=none]+bestaudio/"
            f"best{height}/best"
        )
        postprocessors = [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}]

    opts: dict = {
        "format": fmt,
        "outtmpl": str(options.output_dir / options.filename_template),
        "paths": {"home": str(options.output_dir)},
        "noplaylist": not options.playlist,
        "postprocessors": postprocessors,
        "merge_output_format": None if options.audio_only else "mp4",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 5,
        "fragment_retries": 5,
        "restrictfilenames": False,
        "windowsfilenames": True,
    }
    if options.cookies_from_browser:
        opts["cookiesfrombrowser"] = (options.cookies_from_browser,)
    if options.subtitles:
        opts["writesubtitles"] = True
        opts["writeautomaticsub"] = True
        opts["subtitleslangs"] = ["zh.*", "en.*"]
    return opts


def _final_filepath(info: dict) -> Path | None:
    requested = info.get("requested_downloads") or []
    for item in requested:
        if item.get("filepath"):
            return Path(item["filepath"])
    if info.get("filepath"):
        return Path(info["filepath"])
    return None


def download(
    options: GrabOptions,
    on_progress=None,
) -> list[GrabResult]:
    """Download `options.url` and return one result per file.

    `on_progress` receives a `Progress` snapshot for every yt-dlp hook call.
    """
    if not options.url or not options.url.strip():
        raise GrabitError("No URL given.")
    if options.audio_only and not ffmpeg_available():
        raise GrabitError(
            "Audio extraction needs ffmpeg, which was not found. "
            "Install it (e.g. `brew install ffmpeg`) or drop --audio."
        )

    options.output_dir.mkdir(parents=True, exist_ok=True)
    results: list[GrabResult] = []

    def hook(data: dict) -> None:
        if on_progress is None:
            return
        on_progress(
            Progress(
                status=data.get("status", ""),
                downloaded_bytes=data.get("downloaded_bytes") or 0,
                total_bytes=data.get("total_bytes")
                or data.get("total_bytes_estimate"),
                speed=data.get("speed"),
                eta=data.get("eta"),
                filename=data.get("filename"),
            )
        )

    ydl_opts = build_ydl_opts(options)
    ydl_opts["progress_hooks"] = [hook]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(options.url, download=True)
    except DownloadError as exc:
        raise GrabitError(str(exc).split("ERROR: ")[-1].strip()) from exc
    except YoutubeDLError as exc:
        raise GrabitError(str(exc)) from exc

    if info is None:
        raise GrabitError("Nothing was downloaded.")

    entries = info.get("entries") if info.get("_type") == "playlist" else [info]
    for entry in entries or []:
        if not entry:
            continue
        path = _final_filepath(entry)
        if path is None:
            continue
        results.append(
            GrabResult(
                title=entry.get("title") or path.stem,
                filepath=path,
                extractor=entry.get("extractor_key") or entry.get("extractor") or "",
                duration=entry.get("duration"),
                filesize=entry.get("filesize") or entry.get("filesize_approx"),
            )
        )
    if not results:
        raise GrabitError("Download finished but no output file was found.")
    return results


@dataclass
class ProbeResult:
    title: str
    extractor: str
    duration: float | None
    formats: list[dict] = field(default_factory=list)


def probe(url: str) -> ProbeResult:
    """Fetch metadata without downloading."""
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except YoutubeDLError as exc:
        raise GrabitError(str(exc).split("ERROR: ")[-1].strip()) from exc
    return ProbeResult(
        title=info.get("title") or url,
        extractor=info.get("extractor_key") or "",
        duration=info.get("duration"),
    )
