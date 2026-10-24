"""
Heat To Load // Web Application Local Server
Serves the interactive frontend cockpit at http://localhost:8000
"""

import http.server
import socketserver
import pathlib
import sys
import webbrowser

ROOT = pathlib.Path(__file__).parent.resolve()
WEB_DIR = ROOT / "web"
PORT = 8000

class CustomHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def end_headers(self):
        # Enable CORS and disable aggressive caching for local development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

def run_server(port=PORT, open_browser=False):
    handler = CustomHTTPHandler
    # Try preferred port or find next available
    for p in range(port, port + 10):
        try:
            with socketserver.TCPServer(("", p), handler) as httpd:
                url = f"http://localhost:{p}"
                print("=" * 70)
                print(f"HEAT TO LOAD // Interactive Frontend Cockpit")
                print(f"Serving web application at: {url}")
                print("Press Ctrl+C to stop the server.")
                print("=" * 70)
                if open_browser:
                    webbrowser.open(url)
                httpd.serve_forever()
        except OSError:
            continue

if __name__ == "__main__":
    open_b = "--open" in sys.argv
    run_server(PORT, open_browser=open_b)
