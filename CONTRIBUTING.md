# Contributing to grabit

Thanks for helping. grabit is intentionally small: it wraps yt-dlp for the
"one link, one file" workflow and leaves yt-dlp's hundreds of options alone.
Changes that keep that focus are the most welcome.

## Development setup

You need Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/JiaDing-AlphaTech/grabit
cd grabit
uv run --group dev pytest -q
```

## What to know before changing things

- Site support comes entirely from yt-dlp. A site that fails to download is
  almost always a yt-dlp issue, not a grabit bug — please check there first.
- `tests/` must not touch the network. Use the existing fake `YoutubeDL` in
  `tests/test_core.py` as the pattern.
- The web UI binds to loopback by default and must stay that way. See
  [SECURITY.md](SECURITY.md) before changing `src/grabit/web.py`.
- Keep the public surface in `grabit/__init__.py` (`__all__`) stable.

## Proposing a change

Open an issue first for anything bigger than a small fix, so we can agree on
the shape before you write code. Pull requests should include tests for the
behavior they add or change, and `uv run --group dev pytest -q` should pass.

## Reporting bugs

Use the bug report template and include the output of `grab --version`, the
URL's site (not necessarily the URL itself, if it is private), and the full
error message.
