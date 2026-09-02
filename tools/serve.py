#!/usr/bin/env python3
"""Static preview server with HTTP Range support (needed by PMTiles).

Python's stock http.server ignores Range headers and would send the whole
tileset for every tile request. GitHub Pages honours Range, so this only
matters for local preview.  Usage: python3 tools/serve.py PORT DIRECTORY
"""
import os
import re
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class RangeHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".pmtiles": "application/octet-stream", ".pbf": "application/x-protobuf",
                      ".js": "text/javascript", ".json": "application/json", ".svg": "image/svg+xml"}

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path) or not os.path.exists(path):
            return super().send_head()
        rng = self.headers.get("Range")
        m = re.match(r"bytes=(\d*)-(\d*)$", rng or "")
        if not m:
            self.send_response(200)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Type", self.guess_type(path))
            size = os.path.getsize(path)
            self.send_header("Content-Length", str(size))
            self.end_headers()
            return open(path, "rb")
        size = os.path.getsize(path)
        start = int(m.group(1)) if m.group(1) else 0
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return None
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        f = open(path, "rb")
        f.seek(start)
        self._range_left = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        left = getattr(self, "_range_left", None)
        if left is None:
            return super().copyfile(source, outputfile)
        while left > 0:
            chunk = source.read(min(65536, left))
            if not chunk:
                break
            outputfile.write(chunk)
            left -= len(chunk)
        self._range_left = None

    def log_message(self, fmt, *args):  # quieter console
        if "206" in (args[1] if len(args) > 1 else ""):
            return
        super().log_message(fmt, *args)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8732
    directory = sys.argv[2] if len(sys.argv) > 2 else "."
    handler = partial(RangeHandler, directory=directory)
    print(f"Serving {directory} on http://localhost:{port} (Range supported)")
    ThreadingHTTPServer(("", port), handler).serve_forever()
