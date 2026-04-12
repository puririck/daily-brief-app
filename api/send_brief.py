import sys
import os
from http.server import BaseHTTPRequestHandler

# Allow importing from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from daily_brief_email import main


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Verify Vercel cron secret to block unauthorized triggers
        cron_secret = os.environ.get("CRON_SECRET", "")
        auth_header = self.headers.get("Authorization", "")
        if cron_secret and auth_header != f"Bearer {cron_secret}":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        try:
            main()
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Brief sent successfully")
        except SystemExit:
            # main() calls sys.exit(1) on config errors
            self.send_response(500)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Error: check EMAIL_TO / GMAIL_APP_PASSWORD env vars")
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Error: {e}".encode())
