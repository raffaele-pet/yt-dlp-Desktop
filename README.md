# yt-dlp Desktop

An unofficial Windows desktop app for [yt-dlp](https://github.com/yt-dlp/yt-dlp). Download videos and playlists, choose a resolution, or extract MP3/M4A audio. Includes support for VidXgo players and embeds.

## Install

Requires Windows 10/11, an internet connection, and [WinGet](https://learn.microsoft.com/windows/package-manager/winget/).

1. Download and extract this repository.
2. Run `INSTALL.bat`.
3. Open **yt-dlp Desktop** from the desktop shortcut or run `RUN.vbs`.

The installer reuses Python 3.11+ if available, creates a local `.venv`, and installs missing tools such as FFmpeg and Deno. Python 3.13 is installed only if no compatible version is found.

## Use

Paste a video URL, choose the destination, format, and resolution, then click **Download**. Enable the playlist checkbox to download all items. For playlists, the selected resolution is a maximum.

**Cancel** stops the download; **Open folder** shows saved files. Site restrictions and authentication requirements still apply.

## Update and troubleshoot

- **Update yt-dlp** updates the local download engine and its dependencies.
- Run `INSTALL.bat` again to check and update all required tools.
- Use `INSTALL.bat --check` for a read-only requirements check.
- Use `RUN_DEBUG.cmd` if the app does not start.

Download only content you are authorized to save.
