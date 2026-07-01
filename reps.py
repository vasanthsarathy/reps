"""Launch the reps coding gym: start the server and open the browser."""
import threading
import webbrowser
import uvicorn
from app import config

HOST, PORT = "127.0.0.1", 8000


def _open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    config.ensure_dirs()
    threading.Timer(1.0, _open_browser).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")
