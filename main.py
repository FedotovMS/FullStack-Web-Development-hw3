import mimetypes
import json
import logging
from pathlib import Path
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader


# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Налаштування базових директорій
BASE_DIR = Path(__file__).parent
STORAGE_DIR = BASE_DIR / "storage"
DATA_FILE = STORAGE_DIR / "data.json"
TEMPLATES_DIR = BASE_DIR

#налаштування jinja
jinja = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
PORT=3000

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case "/":
                self.send_html("index.html")
            case "/message.html":
                self.send_html("message.html")
            case "/read":
                self.render_template("read.html")
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html("error.html", 404)

    def do_POST(self) -> None:
        if self.path == "/message":
            size = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(size).decode("utf-8")
            parse_body = urllib.parse.unquote_plus(body)
            data_dict: Dict[str, str] = {
                item.split("=")[0]: item.split("=")[1] for item in parse_body.split("&")
            }

            logger.info(f"Received message: {data_dict}")

            if not STORAGE_DIR.exists():
                STORAGE_DIR.mkdir(parents=True)

            timestamp = datetime.now().isoformat()
            new_entry = {timestamp: data_dict}

            if DATA_FILE.exists():
                with open(DATA_FILE, "r", encoding="utf-8") as file:
                    try:
                        data: Dict[str, Any] = json.load(file)
                    except json.JSONDecodeError:
                        data = {}
            else:
                data = {}

            data.update(new_entry)
            with open(DATA_FILE, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)

            logger.info("Message saved successfully.")

            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def send_html(self, filename: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as file:
            self.wfile.write(file.read())
        logger.info(f"Served HTML file: {filename} with status {status}")

    def render_template(self, filename: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if DATA_FILE.exists():
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                try:
                    messages: Dict[str, Any] = json.load(file)
                except json.JSONDecodeError:
                    messages = {}
        else:
            messages = {}

        template = jinja.get_template(filename)
        content = template.render(messages=messages)
        self.wfile.write(content.encode())
        logger.info(f"Rendered template: {filename}")

    def send_static(self, filename: Path, status: int = 200) -> None:
        self.send_response(status)
        mime_type, *_ = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header("Content-type", mime_type)
        else:
            self.send_header("Content-type", "text/plain")
        self.end_headers()
        with open(filename, "rb") as file:
            self.wfile.write(file.read())
        logger.info(f"Served static file: {filename} with status {status}")


def run() -> None:
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, MyHandler)
    logger.info("Starting server on port 3000...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server is shutting down...")
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()

