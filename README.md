# yt-dlp Desktop

An unofficial Windows desktop app for [yt-dlp](https://github.com/yt-dlp/yt-dlp). Download videos and playlists, choose a resolution, or extract MP3/M4A audio. Includes support for VidXgo players and embeds.

## Install on Windows

Choose **one** method. Both require 64-bit Windows 10/11, an internet connection, and [WinGet](https://learn.microsoft.com/windows/package-manager/winget/). Setup prepares an isolated Python environment with yt-dlp and installs missing tools such as FFmpeg and Deno.

### Option 1 — Windows installer (.exe)

1. Open [Releases → latest](https://github.com/raffaele-pet/yt-dlp-Desktop/releases/latest) and download **`yt-dlp-Desktop-Setup.exe`** under **Assets**.
2. Run the installer. Open **yt-dlp Desktop** from the Start menu or the optional desktop shortcut.

If you already installed the app with the EXE, run the latest installer and choose **Update**. Setup reuses the current installation folder and shows each step in the wizard.

### Option 2 — From the repository

1. Choose **Code → Download ZIP** and extract it, or clone the repository.

   ```sh
   git clone https://github.com/raffaele-pet/yt-dlp-Desktop.git
   ```

2. Open the extracted or cloned folder and run **`INSTALL.bat`**.
3. Open the **yt-dlp Desktop** shortcut or run **`RUN.vbs`** from that folder.

## Use

Paste a video URL, choose the format, resolution, and folder, then click **Download**. For playlists, enable **Download entire playlist**. The selected resolution is a maximum, and the progress bar follows each item.

**MP4 (H.264 / AAC)** is the default for Premiere Pro and other video editors. It copies compatible streams and converts AV1, VP9 and other codecs when needed, including at higher resolutions. Files in this mode have an `(H264)` suffix. If you already downloaded an incompatible file, download the source again in this format.

**Video (original codecs)** preserves the source codecs, which can include AV1 or VP9. **MP3** and **M4A** save audio only.

Use **Open folder** to find the saved files and **Show details** for download diagnostics.

## Update and troubleshoot

- Choose **Tools → Update yt-dlp** to update the download engine.
- To repair setup or update the app, run the latest EXE again, or update the repository and rerun `INSTALL.bat`.
- Use `INSTALL.bat --check` for a read-only requirements check.
- Use `RUN_DEBUG.cmd` if the app does not start.

Download only content you are authorized to save.
