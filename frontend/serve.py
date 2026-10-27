"""
Serves the frontend like `python -m http.server`, but tells the browser never
to cache any file. Plain http.server sends no cache headers at all, so Chrome
and Edge apply their own heuristic caching to app.js/styles.css/index.html -
a plain refresh (even Ctrl+F5 in some cases) can keep showing an old build.
"""
import http.server
import sys


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4321
    http.server.test(HandlerClass=NoCacheHandler, port=port, bind="127.0.0.1")
