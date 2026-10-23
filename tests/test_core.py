from __future__ import annotations

import json
from pathlib import Path

import pytest

from grabit.cli import build_parser, human_size, main
from grabit.core import (
    GrabOptions,
    GrabitError,
    Progress,
    build_ydl_opts,
    download,
    probe,
)


def test_human_size():
    assert human_size(None) == "?"
    assert human_size(0) == "?"
    assert human_size(512) == "512.0 B"
    assert human_size(1536) == "1.5 KB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"


def test_progress_percent():
    assert Progress(downloaded_bytes=25, total_bytes=100).percent == 25
    assert Progress(downloaded_bytes=1, total_bytes=None).percent is None
    assert Progress(downloaded_bytes=1, total_bytes=0).percent is None


def test_invalid_options():
    with pytest.raises(GrabitError):
        GrabOptions(url="https://x", audio_format="aac")
    with pytest.raises(GrabitError):
        GrabOptions(url="https://x", max_height=0)


def test_video_format_selection():
    opts = build_ydl_opts(GrabOptions(url="https://x", max_height=720))
    assert "height<=720" in opts["format"]
    assert "bestaudio" in opts["format"]
    assert opts["merge_output_format"] == "mp4"
    assert opts["noplaylist"] is True
    assert any(p["key"] == "FFmpegVideoRemuxer" for p in opts["postprocessors"])


def test_audio_format_selection():
    opts = build_ydl_opts(GrabOptions(url="https://x", audio_only=True, audio_format="flac"))
    assert opts["format"].startswith("bestaudio")
    extract = opts["postprocessors"][0]
    assert extract["key"] == "FFmpegExtractAudio"
    assert extract["preferredcodec"] == "flac"


def test_optional_flags():
    opts = build_ydl_opts(
        GrabOptions(url="https://x", cookies_from_browser="safari",
                    subtitles=True, playlist=True)
    )
    assert opts["cookiesfrombrowser"] == ("safari",)
    assert opts["writesubtitles"] is True
    assert opts["noplaylist"] is False


def test_output_template_uses_directory(tmp_path: Path):
    opts = build_ydl_opts(GrabOptions(url="https://x", output_dir=tmp_path))
    assert opts["outtmpl"].startswith(str(tmp_path))
    assert "%(title).200B" in opts["outtmpl"]


def test_download_rejects_empty_url(tmp_path: Path):
    with pytest.raises(GrabitError):
        download(GrabOptions(url="   ", output_dir=tmp_path))


def test_download_requires_ffmpeg_for_audio(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("grabit.core.ffmpeg_available", lambda: False)
    with pytest.raises(GrabitError, match="ffmpeg"):
        download(GrabOptions(url="https://x", output_dir=tmp_path, audio_only=True))


class _FakeYDL:
    """Stand-in for yt_dlp.YoutubeDL that never touches the network."""

    instances: list[_FakeYDL] = []

    def __init__(self, opts):
        self.opts = opts
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=True):
        hook = self.opts["progress_hooks"][0]
        hook({"status": "downloading", "downloaded_bytes": 50,
              "total_bytes": 100, "speed": 10, "eta": 5, "filename": "clip.mp4"})
        hook({"status": "finished", "filename": "clip.mp4",
              "downloaded_bytes": 100, "total_bytes": 100})
        return {
            "title": "Clip",
            "extractor_key": "Example",
            "duration": 12,
            "requested_downloads": [{"filepath": "/tmp/clip.mp4"}],
        }


def test_download_reports_progress_and_result(tmp_path: Path, monkeypatch):
    _FakeYDL.instances = []
    monkeypatch.setattr("grabit.core.yt_dlp.YoutubeDL", _FakeYDL)
    seen = []
    results = download(
        GrabOptions(url="https://example.com/v", output_dir=tmp_path),
        on_progress=seen.append,
    )
    assert [p.status for p in seen] == ["downloading", "finished"]
    assert seen[0].percent == 50
    assert results[0].title == "Clip"
    assert results[0].filepath == Path("/tmp/clip.mp4")
    assert results[0].extractor == "Example"
    assert _FakeYDL.instances[0].opts["noplaylist"] is True


def test_download_wraps_yt_dlp_errors(tmp_path: Path, monkeypatch):
    from yt_dlp.utils import DownloadError

    class _Boom(_FakeYDL):
        def extract_info(self, url, download=True):
            raise DownloadError("ERROR: unsupported URL")

    monkeypatch.setattr("grabit.core.yt_dlp.YoutubeDL", _Boom)
    with pytest.raises(GrabitError, match="unsupported URL"):
        download(GrabOptions(url="https://nope", output_dir=tmp_path))


def test_probe(monkeypatch):
    class _Info(_FakeYDL):
        def extract_info(self, url, download=True):
            assert download is False
            return {"title": "Meta", "extractor_key": "Example", "duration": 3}

    monkeypatch.setattr("grabit.core.yt_dlp.YoutubeDL", _Info)
    meta = probe("https://example.com/v")
    assert meta.title == "Meta"
    assert meta.duration == 3


def test_cli_info(monkeypatch, capsys):
    monkeypatch.setattr("grabit.cli.probe",
                        lambda url: type("M", (), {"title": "T", "extractor": "E",
                                                    "duration": 9})())
    assert main(["https://example.com/v", "--info"]) == 0
    assert "T" in capsys.readouterr().out


def test_cli_rejects_non_url(capsys):
    assert main(["not a link"]) == 2
    assert "does not look like a URL" in capsys.readouterr().err


def test_cli_uses_clipboard_when_no_url(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("grabit.cli.read_clipboard", lambda: "https://example.com/v")

    def fake_download(options, on_progress=None):
        assert options.url == "https://example.com/v"
        assert options.output_dir == tmp_path
        from grabit.core import GrabResult
        return [GrabResult("T", tmp_path / "t.mp4", "E", 1, 10)]

    monkeypatch.setattr("grabit.cli.download", fake_download)
    assert main(["-o", str(tmp_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["title"] == "T"


def test_cli_no_url_anywhere(monkeypatch, capsys):
    monkeypatch.setattr("grabit.cli.read_clipboard", lambda: "")
    assert main([]) == 2


def test_parser_defaults():
    args = build_parser().parse_args(["https://x"])
    assert args.audio is False
    assert args.audio_format == "mp3"
    assert args.playlist is False


def test_package_exports():
    import grabit

    assert grabit.download is download
    assert grabit.GrabOptions is GrabOptions


def test_clipboard_falls_back_between_tools(monkeypatch):
    import subprocess

    import grabit.cli as cli

    monkeypatch.setattr(cli, "_clipboard_commands", lambda: [["missing-tool"], ["second"]])

    def fake_run(cmd, **kwargs):
        if cmd == ["missing-tool"]:
            raise FileNotFoundError(cmd[0])
        return subprocess.CompletedProcess(cmd, 0, stdout=" https://x \n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert cli.read_clipboard() == "https://x"


def test_clipboard_empty_when_no_tool(monkeypatch):
    import grabit.cli as cli

    monkeypatch.setattr(cli, "_clipboard_commands", lambda: [["definitely-not-a-real-tool-xyz"]])
    assert cli.read_clipboard() == ""


def test_version_flag(capsys):
    import grabit

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert grabit.__version__ in capsys.readouterr().out
