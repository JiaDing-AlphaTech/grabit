# grabit

[![tests](https://github.com/JiaDing-AlphaTech/grabit/actions/workflows/tests.yml/badge.svg)](https://github.com/JiaDing-AlphaTech/grabit/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

Paste one link, get the file.

`grabit` is a small, friendly wrapper around [yt-dlp](https://github.com/yt-dlp/yt-dlp).
yt-dlp supports hundreds of sites and exposes hundreds of options; grabit keeps
the one workflow most people actually want: **give it a URL, get the best
available video (or just the audio) in your downloads folder.**

```bash
grab "https://www.youtube.com/watch?v=..."
```

## Install

Requires Python 3.11+ and, for audio extraction and merging high-quality
video with audio, [ffmpeg](https://ffmpeg.org/).

```bash
# macOS
brew install ffmpeg
# Debian/Ubuntu
sudo apt install ffmpeg
# Windows
winget install ffmpeg

pip install grabit-dl
```

The package is published as `grabit-dl` because the `grabit` name on PyPI
already belongs to an unrelated project. The commands it installs are still
`grab` and `grab-web`.

Or run it straight from the repository, without installing:

```bash
uvx --from git+https://github.com/JiaDing-AlphaTech/grabit grab "<url>"
```

## Usage

```bash
grab "<url>"                     # best quality mp4 into ~/Downloads
grab                             # no URL: use whatever is on the clipboard
grab "<url>" -a                  # audio only, saved as mp3
grab "<url>" -a --audio-format flac
grab "<url>" --max-height 1080   # cap the resolution
grab "<url>" --subs              # also grab subtitles (zh, en)
grab "<url>" --playlist          # the whole playlist, not just one item
grab "<url>" -o ~/Movies         # choose the output directory
grab "<url>" --info              # show the title, don't download
grab "<url>" --cookies-from-browser safari   # for sites that need a login
```

### Local web page

If you would rather paste the link into a browser:

```bash
grab-web
```

This opens `http://127.0.0.1:8787`. Nothing leaves your machine: the page is
served locally and files are saved to `~/Downloads`. It only accepts requests
from your own browser; see [SECURITY.md](SECURITY.md) before using `--host`
to expose it.

## What it downloads

- **Video:** the best video track plus the best audio track, merged into an
  mp4. If a site only offers a pre-merged file, that is used instead.
- **Audio (`-a`):** the best audio track, converted with ffmpeg.
- **Playlists:** only the single item the link points at, unless you pass
  `--playlist`.

## Programmatic use

```python
from grabit import GrabOptions, download

results = download(GrabOptions(url="https://example.com/watch?v=1"))
print(results[0].filepath)
```

## Legal

grabit downloads media the same way your browser does. It is your
responsibility to respect the terms of service of each site and the copyright
of the content. Only download material you have the right to download.

grabit is built on [yt-dlp](https://github.com/yt-dlp/yt-dlp), which is
licensed under the Unlicense. All credit for site support belongs to the
yt-dlp contributors.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Changes are listed in
[CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE).

## 中文简介

`grabit` 是 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 的一个轻量封装：给一个链接，
把画质最好的视频（或只要音频）下载到下载文件夹，省去 yt-dlp 的上百个参数。

```bash
pip install grabit-dl          # PyPI 上的包名，命令仍是 grab
grab "<链接>"                  # 最佳画质，保存为 mp4
grab "<链接>" -a               # 只保留音频，存为 mp3
grab-web                       # 打开本地网页 http://127.0.0.1:8787 粘贴链接
```

下载内容时请遵守各网站的服务条款和版权要求，只下载你有权下载的内容。
