import json
import os

from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
from yt_dlp.utils import PostProcessingError, prepend_extension, replace_extension


class DesktopCompatiblePP(FFmpegPostProcessor):
    """Produce an editing-friendly MP4, copying streams that are already compatible."""

    def __init__(self, downloader=None):
        super().__init__(downloader)
        if downloader is not None:
            downloader.params["final_ext"] = "mp4"

    def run(self, info):
        source = info["filepath"]
        if not self.probe_available:
            raise PostProcessingError("FFprobe is required for MP4 (H.264 / AAC). Reinstall FFmpeg.")
        try:
            media = self.get_metadata_object(source)
        except (OSError, json.JSONDecodeError) as exc:
            raise PostProcessingError(f"Could not inspect the downloaded video: {exc}") from exc

        streams = media.get("streams", [])
        video = next((stream for stream in streams if stream["codec_type"] == "video"
                      and not stream.get("disposition", {}).get("attached_pic")), None)
        if not video:
            raise PostProcessingError("The downloaded file has no video stream.")
        audio = next((stream for stream in streams if stream["codec_type"] == "audio"), None)
        copy_video = video["codec_name"] == "h264" and video.get("pix_fmt") == "yuv420p"
        copy_audio = not audio or (audio["codec_name"] == "aac" and audio.get("profile") == "LC")
        if copy_video and copy_audio and "mp4" in media["format"]["format_name"].split(",") and info["ext"] == "mp4":
            return [], info

        target = replace_extension(source, "mp4", info["ext"])
        temporary = prepend_extension(target, "encoding")
        options = ["-map", "0:V:0", "-map", "0:a:0?", "-c", "copy", "-tag:v", "avc1"]
        if not copy_video:
            options += [
                "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            ]
        if not copy_audio:
            options += ["-c:a", "aac", "-profile:a", "aac_low", "-b:a", "256k"]

        self.to_screen("Converting to H.264 / AAC" if not (copy_video and copy_audio) else "Writing the MP4 container")
        try:
            self.run_ffmpeg(source, temporary, options)
            os.replace(temporary, target)
        except (OSError, PostProcessingError):
            if os.path.exists(temporary):
                os.remove(temporary)
            raise
        info.update(filepath=target, ext="mp4", vcodec="h264", acodec="aac" if audio else "none")
        return ([] if source == target else [source]), info
