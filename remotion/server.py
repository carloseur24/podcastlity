#!/usr/bin/env python3
"""
Simple HTTP server for Remotion video rendering.
Serves video files and static content for Remotion's headless browser.
"""

import http.server
import socketserver
import os
import sys
import time
import threading
import json

PORT = 8765


class RemotionHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for Remotion video serving."""

    def __init__(self, *args, directory=None, **kwargs):
        self.video_file = None
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        if self.path == "/video.mp4" and self.video_file:
            # Serve video file
            try:
                with open(self.video_file, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-Type", "video/mp4")
                    self.send_header("Content-Length", os.path.getsize(self.video_file))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(f.read())
            except Exception as e:
                self.send_error(500, str(e))
        else:
            # Default: serve static files
            super().do_GET()

    def log_message(self, format, *args):
        # Custom logging
        print(f"[server] {args[0]}")


def start_server(video_path, static_dir=None, port=PORT):
    """Start the HTTP server."""

    # Set the video file to serve
    RemotionHandler.video_file = video_path

    # Change to the static directory if provided
    if static_dir and os.path.exists(static_dir):
        os.chdir(static_dir)

    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", port), RemotionHandler) as httpd:
        print(f"[server] Serving on http://localhost:{port}")
        print(f"[server] Video: {video_path}")
        print(f"[server] Static: {static_dir or 'N/A'}")
        httpd.serve_forever()


def start_server_background(video_path, static_dir=None, port=PORT):
    """Start server in background thread."""
    thread = threading.Thread(
        target=start_server, args=(video_path, static_dir, port), daemon=True
    )
    thread.start()
    time.sleep(1)  # Wait for server to start
    return port


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: server.py <video_file> [static_dir] [port]")
        sys.exit(1)

    video_file = sys.argv[1]
    static_dir = sys.argv[2] if len(sys.argv) > 2 else None
    port = int(sys.argv[3]) if len(sys.argv) > 3 else PORT

    start_server(video_file, static_dir, port)
