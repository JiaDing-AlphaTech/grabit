# Security policy

## Supported versions

Only the latest release is supported with security fixes.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Instead, use
[GitHub private vulnerability reporting](https://github.com/JiaDing-AlphaTech/grabit/security/advisories/new)
so we can look at it before it is public. We aim to acknowledge reports within
a week.

## Design notes

`grab-web` is a local tool and is built with that assumption:

- It binds to `127.0.0.1` by default. Binding to any other address prints a
  warning, because the UI has no authentication: anyone who can reach it can
  make the machine download files.
- Requests whose `Host` header is not the bound host are rejected, which
  blocks DNS rebinding.
- Requests carrying an `Origin` from another host are rejected, and `POST`
  requires a JSON content type so browsers preflight cross-origin calls. This
  stops a web page you visit from driving the local server.
- Request bodies are capped at 16 KB.

grabit downloads whatever URL it is given, through yt-dlp. Only point it at
content you have the right to download.
