"""Lanceur du service Produits : python run.py [--host H] [--port P] [--delay-ms N] [--mode normal|unavailable]."""
import argparse
import os
import signal
import sys
import threading
from products_service.data import DEFAULT_PORT
from products_service.http import create_server


def bounded(value, name, low, high):
    try:
        number = int(value)
    except ValueError:
        raise ValueError(f"{name} doit être un entier.") from None
    if not low <= number <= high:
        raise ValueError(f"{name} doit être compris entre {low} et {high}.")
    return number


def main():
    parser = argparse.ArgumentParser(description="Service Produits (mini-projet EADL FE)")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, help="Défaut : PRODUCTS_PORT ou 8002")
    parser.add_argument("--delay-ms", type=int, help="De 0 à 30000. Défaut : PRODUCTS_DELAY_MS ou 0")
    parser.add_argument("--mode", choices=("normal", "unavailable"), help="Défaut : PRODUCTS_MODE ou normal")
    args = parser.parse_args()
    port = bounded(args.port if args.port is not None else os.environ.get("PRODUCTS_PORT", DEFAULT_PORT), "port", 1, 65535)
    delay = bounded(args.delay_ms if args.delay_ms is not None else os.environ.get("PRODUCTS_DELAY_MS", 0), "delay-ms", 0, 30000)
    mode = args.mode or os.environ.get("PRODUCTS_MODE", "normal")
    if mode not in ("normal", "unavailable"):
        raise ValueError("PRODUCTS_MODE doit valoir normal ou unavailable.")
    server = create_server(args.host, port, delay, mode)
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
    worker.start()
    print(f"[products] http://{args.host}:{port}/api/products (mode={mode}, délai={delay} ms)", flush=True)
    try:
        stop.wait()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(f"Impossible de démarrer : {error}", file=sys.stderr)
        sys.exit(1)