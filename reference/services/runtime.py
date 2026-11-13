"""Hébergement Uvicorn utilisé par les lanceurs et les tests réseau.

Le socket est réservé dès la création, y compris avec port=0 dans les tests.
Les objets FastAPI restent utilisables directement avec TestClient.
"""
import socket
import threading
import uvicorn

class AsgiServer:
    def __init__(self, app, host="127.0.0.1", port=0):
        self.app = app
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.bind((host, port))
            self.socket.listen(128)
        except BaseException:
            self.socket.close()
            raise
        self.server_port = self.socket.getsockname()[1]
        self.server_address = (host, self.server_port)
        self.done = threading.Event()
        self.server = uvicorn.Server(uvicorn.Config(
            app, host=host, port=self.server_port, access_log=False,
            log_level="critical", log_config=None, server_header=False,
            proxy_headers=False, timeout_graceful_shutdown=1, lifespan="on"))

    def serve_forever(self, poll_interval=0.1):
        try:
            self.server.run(sockets=[self.socket])
        finally:
            self.done.set()

    def shutdown(self):
        self.server.should_exit = True
        if not self.done.wait(10):
            raise RuntimeError("Uvicorn ne s'est pas arrêté dans le délai prévu.")

    def server_close(self):
        self.socket.close()
