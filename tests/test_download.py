import functools
import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import app


class ThrottledHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def copyfile(self, source, output):
        try:
            while chunk := source.read(4096):
                output.write(chunk)
                output.flush()
                time.sleep(0.035)
        except (BrokenPipeError, ConnectionResetError):
            pass  # The generic extractor only reads the first bytes when identifying the URL.


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg and FFprobe are required")
class DownloadTests(unittest.TestCase):
    def test_av1_download_reports_progress_and_produces_editable_mp4(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "fixture.webm"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "testsrc2=size=480x270:rate=24",
                "-f", "lavfi", "-i", "sine=frequency=500:sample_rate=48000",
                "-t", "3", "-c:v", "libaom-av1", "-cpu-used", "8", "-threads", "2",
                "-b:v", "400k", "-c:a", "libopus", str(source),
            ], check=True)

            handler = functools.partial(ThrottledHandler, directory=temp)
            with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    url = f"http://127.0.0.1:{server.server_port}/{source.name}"
                    output = base / "downloads"
                    command = app.build_command(sys.executable, url, str(output), app.COMPATIBLE_MP4, False)
                    command[1:1] = ["-m", "yt_dlp"]
                    result = subprocess.run(command, capture_output=True, encoding="utf-8", timeout=45)
                    self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                    self.assertIn("Converting to H.264 / AAC", result.stdout)

                    progress = app.TransferProgress([])
                    samples = [
                        progress.update(*json.loads(line.removeprefix("PROGRESS:")))
                        for line in result.stdout.splitlines() if line.startswith("PROGRESS:")
                    ]
                    self.assertTrue(any(value is not None and 0 < value < 100 for value in samples), result.stdout)
                    self.assertEqual(samples[-1], 100)

                    files = [
                        Path(json.loads(line.removeprefix("FILE:")))
                        for line in result.stdout.splitlines() if line.startswith("FILE:")
                    ]
                    self.assertEqual(len(files), 1, result.stdout)
                    self.assertEqual(files[0].parent, output)
                    self.assertEqual(files[0].suffix, ".mp4")
                    probe = subprocess.run([
                        "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(files[0]),
                    ], check=True, capture_output=True, text=True)
                    video, audio = json.loads(probe.stdout)["streams"]
                    self.assertEqual((video["codec_name"], video["pix_fmt"]), ("h264", "yuv420p"))
                    self.assertEqual((video["width"], video["height"], video["r_frame_rate"]), (480, 270, "24/1"))
                    self.assertEqual((audio["codec_name"], audio["profile"]), ("aac", "LC"))

                    # A repeat should use the existing compatible output and still report the final path.
                    repeat = subprocess.run(command, capture_output=True, encoding="utf-8", timeout=45)
                    self.assertEqual(repeat.returncode, 0, repeat.stderr + repeat.stdout)
                    self.assertNotIn("Converting to H.264 / AAC", repeat.stdout)
                    self.assertIn("FILE:", repeat.stdout)
                finally:
                    server.shutdown()
                    thread.join()
