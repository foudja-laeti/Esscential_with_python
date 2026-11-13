"""Lanceur multiplateforme : python run.py [--service users|products|orders]."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from services.data import DEFAULT_PORTS
from services.http import create_server


def bounded(value, name, low, high):
    try:
        number = int(value)
    except ValueError:
        raise ValueError(f"{name} doit être un entier.") from None
    if not low <= number <= high:
        raise ValueError(f"{name} doit être compris entre {low} et {high}.")
    return number


def install_signals(stop):
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())


def serve(service, host, port, delay, mode):
    server = create_server(service, host, port, delay, mode)
    stop = threading.Event()
    install_signals(stop)
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    worker.start()
    print(f"[{service}] http://{host}:{port}/api/{service} (mode={mode}, délai={delay} ms)", flush=True)
    try:
        stop.wait()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description="Services REST du mini-projet EADL FE")
    parser.add_argument("--service", choices=tuple(DEFAULT_PORTS), help="Un seul service ; sinon lance les trois processus.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, help="Seulement avec --service")
    parser.add_argument("--delay-ms", type=int, help="Seulement avec --service, de 0 à 30000")
    parser.add_argument("--mode", choices=("normal", "unavailable"), help="Seulement avec --service")
    args = parser.parse_args()
    if not args.service and any(value is not None for value in (args.port, args.delay_ms, args.mode)):
        parser.error("--port, --delay-ms et --mode exigent --service.")
    configs = {}
    for name in ([args.service] if args.service else DEFAULT_PORTS):
        upper = name.upper()
        port = bounded(str(args.port if args.port is not None else os.environ.get(upper + "_PORT", DEFAULT_PORTS[name])), "port", 1, 65535)
        delay = bounded(str(args.delay_ms if args.delay_ms is not None else os.environ.get(upper + "_DELAY_MS", 0)), "delay-ms", 0, 30000)
        mode = args.mode or os.environ.get(upper + "_MODE", "normal")
        if mode not in ("normal", "unavailable"):
            raise ValueError(f"{upper}_MODE doit valoir normal ou unavailable.")
        configs[name] = (port, delay, mode)
    if len({c[0] for c in configs.values()}) != len(configs):
        raise ValueError("Les trois ports doivent être différents.")
    if args.service:
        serve(args.service, args.host, *configs[args.service])
        return 0
    children = []
    stop = threading.Event()
    install_signals(stop)
    try:
        for name, (port, delay, mode) in configs.items():
            command = [sys.executable, "-u", str(Path(__file__).resolve()), "--service", name,
                       "--host", args.host, "--port", str(port), "--delay-ms", str(delay), "--mode", mode]
            children.append(subprocess.Popen(command, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)))
        print("Trois processus lancés. Ctrl+C arrête l'ensemble. Les lignes d'écoute confirment les démarrages.", flush=True)
        while not stop.wait(0.1):
            if any(child.poll() is not None for child in children):
                print("Un service s'est arrêté. Arrêt des autres services.", file=sys.stderr)
                return 1
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(f"Impossible de démarrer : {error}", file=sys.stderr)
        sys.exit(1)
