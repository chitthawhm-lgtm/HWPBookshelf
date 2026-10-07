from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # /books.json သို့မဟုတ် ပင်မလိပ်စာ ဝင်လာပါက books.json ဖိုင်ကို တိုက်ရိုက်ပြသမည်
        if self.path == '/books.json' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            if os.path.exists('books.json'):
                with open('books.json', 'r', encoding='utf-8') as f:
                    content = f.read()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.wfile.write(b'[]')
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Server is running!")
            
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run():
    # Render မှ သတ်မှတ်ပေးထားသော Port 10000 ဖြင့် ချိတ်ဆက်ခြင်း
    server_address = ('', 10000)
    httpd = HTTPServer(server_address, SimpleHandler)
    print("Starting HTTP server on port 10000...")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
