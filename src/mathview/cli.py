"""Entry point: a native window by default, a browser URL with --web."""

from __future__ import annotations

import socket
import threading

import typer
import uvicorn

from mathview.server import create_app


def find_free_port() -> int:
    """Ask the OS for an unused port, so two instances never collide."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def serve_forever(port: int) -> None:
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning")


def _serve_background(port: int) -> None:
    server = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True).start()


app = typer.Typer(add_completion=False, help="See how maths works.")


@app.command()
def main(
    web: bool = typer.Option(False, "--web", help="Serve in a browser instead."),
) -> None:
    port = find_free_port()

    if web:
        typer.echo(f"MathView on http://127.0.0.1:{port}")
        serve_forever(port)
        return

    from mathview.shell import open_window

    _serve_background(port)
    open_window(f"http://127.0.0.1:{port}/")
