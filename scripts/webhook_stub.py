import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))


class WebhookStubHandler(BaseHTTPRequestHandler):
    server_version = "ConversionEngineWebhookStub/0.1"

    def _write_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(
            f"{self.client_address[0]} [{self.log_date_time_string()}] {fmt % args}",
            flush=True,
        )

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write_json(
                200,
                {
                    "status": "ok",
                    "service": "conversion-engine",
                    "port": APP_PORT,
                },
            )
            return

        self._write_json(404, {"status": "not_found", "path": self.path})

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b""

        try:
            body_text = raw_body.decode("utf-8")
        except UnicodeDecodeError:
            body_text = raw_body.hex()

        self._write_json(
            202,
            {
                "status": "received",
                "path": self.path,
                "content_type": self.headers.get("Content-Type"),
                "body_preview": body_text[:2000],
            },
        )


def main() -> None:
    server = ThreadingHTTPServer((APP_HOST, APP_PORT), WebhookStubHandler)
    print(
        f"Webhook stub listening on http://{APP_HOST}:{APP_PORT} "
        f"(health: http://{APP_HOST}:{APP_PORT}/health)",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
