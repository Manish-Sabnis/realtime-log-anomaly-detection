"""
app.py
Ingestor-API server entry point.

Usage
-----
    python3 services/ingestor-api/app.py [--port 7000]

Runs a threaded HTTP server on the given port (default 7000).
All routes are defined in routes.py.
Database is initialised in storage.py.
"""

import sys
import argparse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Make sure sibling modules are importable when run from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from storage import init_db
from routes import (
    handle_ingest,
    handle_ingest_batch,
    handle_get_logs,
    handle_get_anomalies,
    handle_status,
)

class IngestorHandler(BaseHTTPRequestHandler):
    """Maps HTTP method + path → route handler."""

    # Suppress default 'GET /path HTTP/1.1 200 -' logs to keep stdout clean
    def log_message(self, fmt, *args):  # type: ignore[override]
        pass

    def do_OPTIONS(self):
        """CORS preflight — needed for dashboard fetch() calls."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/ingest":
            handle_ingest(self)
        elif path == "/ingest/batch":
            handle_ingest_batch(self)
        else:
            self._not_found()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/status":
            handle_status(self)
        elif path == "/logs":
            handle_get_logs(self)
        elif path == "/anomalies":
            handle_get_anomalies(self)
        else:
            self._not_found()

    def _not_found(self):
        import json
        body = json.dumps({"error": "Not found"}).encode()
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description="Log Ingestor API")
    parser.add_argument("--port", type=int, default=7000, help="Port to listen on (default: 7000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    # Initialise database (creates tables if needed)
    print("[ingestor-api] Initialising database...")
    init_db()
    print("[ingestor-api] Database ready.")

    # ThreadingHTTPServer handles each request in its own thread
    class ThreadedHTTPServer(HTTPServer):
        def process_request(self, request, client_address):
            t = threading.Thread(target=self._process_request_thread,
                                 args=(request, client_address))
            t.daemon = True
            t.start()

        def _process_request_thread(self, request, client_address):
            try:
                self.finish_request(request, client_address)
            except Exception:
                self.handle_error(request, client_address)
            finally:
                self.shutdown_request(request)

    server = ThreadedHTTPServer((args.host, args.port), IngestorHandler)
    print(f"[ingestor-api] Listening on http://{args.host}:{args.port}")
    print(f"[ingestor-api] Routes:")
    print(f"  POST  http://localhost:{args.port}/ingest")
    print(f"  POST  http://localhost:{args.port}/ingest/batch")
    print(f"  GET   http://localhost:{args.port}/logs")
    print(f"  GET   http://localhost:{args.port}/anomalies")
    print(f"  GET   http://localhost:{args.port}/status")
    print(f"[ingestor-api] Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[ingestor-api] Shutting down.")
        server.server_close()


if __name__ == "__main__":
    main()