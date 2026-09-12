"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                THE WAX & QUILL · LOCAL LETTERS COMPANION SERVER              ║
║  Run this script to enable one-click direct file saving from your browser!   ║
║  Usage: python manage.py                                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import http.server
import socketserver
import os
import json
import webbrowser
import urllib.request

PORT = 8765
LETTERS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(LETTERS_DIR)
LETTERS_JS_PATH = os.path.join(LETTERS_DIR, 'letters.js')
INDEX_HTML_PATH = os.path.join(ROOT_DIR, 'index.html')

class LetterStudioHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=LETTERS_DIR, **kwargs)

    def do_POST(self):
        if self.path == '/api/save':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length).decode('utf-8')
                data = json.loads(body)
                letters = data.get('letters', [])

                # Preserve SWAN_SEAL_B64 from existing file
                b64_line = ""
                if os.path.exists(LETTERS_JS_PATH):
                    with open(LETTERS_JS_PATH, 'r', encoding='utf-8') as f:
                        old_txt = f.read()
                        if 'window.SWAN_SEAL_B64' in old_txt:
                            for l in old_txt.splitlines():
                                if l.startswith('window.SWAN_SEAL_B64'):
                                    b64_line = l + '\n\n'
                                    break

                # Generate clean formatted letters.js
                formatted_json = json.dumps(letters, indent=2, ensure_ascii=False)
                js_content = (
                    "// =========================================================================\n"
                    "// NEBBIE'S LETTERS ARCHIVE (Source of Truth)\n"
                    "// Generated and managed by The Wax & Quill Studio (letters/index.html)\n"
                    "// =========================================================================\n\n"
                    f"{b64_line}"
                    f"window.LOVE_LETTERS = {formatted_json};\n"
                )

                with open(LETTERS_JS_PATH, 'w', encoding='utf-8') as f:
                    f.write(js_content)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {
                    "success": True,
                    "message": f"Successfully saved {len(letters)} letters to letters/letters.js!"
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
                print(f"[SUCCESS] Saved {len(letters)} letters to {LETTERS_JS_PATH}")
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
                print(f"[ERROR] Failed to save: {e}")
        else:
            self.send_error(404, "Endpoint not found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

if __name__ == '__main__':
    os.chdir(LETTERS_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), LetterStudioHandler) as httpd:
        url = f"http://localhost:{PORT}/index.html"
        print(f"\n🌸 The Wax & Quill Letter Studio is running at: {url}")
        print("Press Ctrl+C to stop the local server.\n")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server. Goodbye! ✨")
