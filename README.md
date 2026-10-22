# grabit

Paste one link, get the file.

`grabit` is a small, friendly wrapper around [yt-dlp](https://github.com/yt-dlp/yt-dlp).
yt-dlp supports hundreds of sites and exposes hundreds of options; grabit keeps
the one workflow most people actually want: **give it a URL, get the best
available video (or just the audio) in your downloads folder.**

```bash
grab "https://www.youtube.com/watch?v=..."
```

## Install

Requires Python 3.10+ and, for audio extraction and merging high-quality
video with audio, [ffmpeg](https://ffmpeg.org/).

```bash
# macOS
brew install ffmpeg
# Debian/Ubuntu
sudo apt install ffmpeg

pip install grabit
```

Or run it straight from the repository:

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
served locally and files are saved to `~/Downloads`.

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

## License

MIT. See [LICENSE](LICENSE).
