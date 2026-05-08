#!/usr/bin/env python3
"""Minimal static server with no-cache headers so deploys are immediately
visible. Python's stock http.server omits Cache-Control, which lets browsers
heuristically cache the pygbag bundle for hours."""
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        # Pygbag fetches need to read response across iframes/workers
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "credentialless")
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3078
    directory = sys.argv[2] if len(sys.argv) > 2 else "static"
    os.chdir(directory)
    print(f"[databreach] serving {directory} on :{port} with no-cache", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), NoCacheHandler).serve_forever()


if __name__ == "__main__":
    main()
