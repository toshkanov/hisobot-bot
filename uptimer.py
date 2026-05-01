from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Hisobot-bot is awake!")

    def log_message(self, format, *args):
        return

def run_uptimer(port):
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

def start_uptimer():
    # Render beradigan portni olamiz
    port = int(os.environ.get("PORT", 8000))
    thread = threading.Thread(target=run_uptimer, args=(port,), daemon=True)
    thread.start()
