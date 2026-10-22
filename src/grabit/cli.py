"""`grab` command: one URL in, one file out."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from grabit.core import AUDIO_FORMATS, GrabOptions, GrabitError, download, probe


def read_clipboard() -> str:
    try:
        import subprocess

        out = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=5, check=False
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def human_size(num: int | None) -> str:
    if not num:
        return "?"
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="grab",
        description="Download a video or audio file from a single link.",
    )
    parser.add_argument("url", nargs="?", help="Page or media URL. Omit to use the clipboard.")
    parser.add_argument("-o", "--output", default="~/Downloads", help="Output directory.")
    parser.add_argument("-a", "--audio", action="store_true", help="Keep audio only.")
    parser.add_argument(
        "--audio-format",
        default="mp3",
        choices=AUDIO_FORMATS,
        help="Audio format used with --audio (default: mp3).",
    )
    parser.add_argument("--max-height", type=int, help="Limit video height, e.g. 1080.")
    parser.add_argument("--subs", action="store_true", help="Also download subtitles.")
    parser.add_argument("--playlist", action="store_true", help="Download the whole playlist.")
    parser.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="Use cookies from a browser (chrome, safari, firefox, ...).",
    )
    parser.add_argument("--info", action="store_true", help="Show metadata, don't download.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    return parser


def make_progress_printer():
    last = ""

    def printer(progress) -> None:
        nonlocal last
        if progress.status == "finished":
            line = "done"
        elif progress.percent is not None:
            line = (
                f"{progress.percent:5.1f}%  "
                f"{human_size(int(progress.speed or 0))}/s  "
                f"eta {int(progress.eta or 0)}s"
            )
        else:
            line = f"{human_size(progress.downloaded_bytes)} downloaded"
        if line != last:
            print("\r" + line.ljust(40), end="", file=sys.stderr, flush=True)
            last = line

    return printer


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    url = (args.url or "").strip() or read_clipboard()
    if not url:
        print("error: give a URL, or copy one to the clipboard.", file=sys.stderr)
        return 2
    if "://" not in url:
        print(f"error: '{url}' does not look like a URL.", file=sys.stderr)
        return 2

    try:
        if args.info:
            meta = probe(url)
            print(f"{meta.title}\nfrom {meta.extractor or 'unknown'}"
                  + (f", {int(meta.duration)}s" if meta.duration else ""))
            return 0

        options = GrabOptions(
            url=url,
            output_dir=Path(args.output),
            audio_only=args.audio,
            audio_format=args.audio_format,
            max_height=args.max_height,
            cookies_from_browser=args.cookies_from_browser,
            subtitles=args.subs,
            playlist=args.playlist,
        )
        results = download(options, on_progress=None if args.json else make_progress_printer())
    except GrabitError as exc:
        print(f"\nerror: {exc}", file=sys.stderr)
        return 1

    if not args.json:
        print(file=sys.stderr)
    for result in results:
        if args.json:
            import json

            print(json.dumps({"title": result.title, "path": str(result.filepath)}))
        else:
            print(f"saved: {result.filepath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
