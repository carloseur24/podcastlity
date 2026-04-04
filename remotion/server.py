#!/usr/bin/env python3
"""
Simple HTTP server for Remotion video rendering.
"""

import http.server
import socketserver
import os
import sys

PORT = 8765


class RemotionHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for Remotion video serving."""

    def do_GET(self):
        if self.path == "/video.mp4" or self.path == "/input_video.mp4":
            # Try to serve from the video_file class variable or default location
            video_path = getattr(self.__class__, "video_file", None)

            if not video_path:
                # Check common locations
                for candidate in ["public/input_video.mp4", "input_video.mp4"]:
                    if os.path.exists(candidate):
                        video_path = candidate
                        break

            if video_path and os.path.exists(video_path):
                try:
                    with open(video_path, "rb") as f:
                        self.send_response(200)
                        self.send_header("Content-Type", "video/mp4")
                        self.send_header("Content-Length", os.path.getsize(video_path))
                        self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                        self.send_header("Access-Control-Allow-Headers", "*")
                        self.end_headers()
                        self.wfile.write(f.read())
                    return
                except Exception as e:
                    self.send_error(500, str(e))
                    return
            else:
                self.send_error(404, f"Video file not found. Tried: {video_path}")
                return
        elif self.path == "/":
            # Serve index.html or list directory
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Remotion Video Server</h1><p>Video available at /video.mp4</p></body></html>"
            )
            return

        # Default: try to serve from current directory
        super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, format, *args):
        print(f"[server] {args[0]}")


def start_server(video_path, static_dir=None, port=PORT):
    """Start the HTTP server."""

    # Set the video file as class variable
    RemotionHandler.video_file = video_path

    # Change to the static directory if provided
    if static_dir and os.path.exists(static_dir):
        os.chdir(static_dir)
        print(f"[server] Changed directory to: {static_dir}")

    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", port), RemotionHandler) as httpd:
        print(f"[server] Serving on http://localhost:{port}")
        print(f"[server] Video: {video_path}")
        print(f"[server] Static: {static_dir or 'N/A'}")
        httpd.serve_forever()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: server.py <video_file> [static_dir] [port]")
        sys.exit(1)

    video_file = sys.argv[1]
    static_dir = sys.argv[2] if len(sys.argv) > 2 else None
    port = int(sys.argv[3]) if len(sys.argv) > 3 else PORT

    start_server(video_file, static_dir, port)
