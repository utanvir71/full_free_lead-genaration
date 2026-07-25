from __future__ import annotations

import socket
from collections.abc import Iterator
from dataclasses import dataclass
from threading import Thread
from time import monotonic, sleep

import httpx
import pytest
import uvicorn
from fastapi import FastAPI

from app.config import Settings
from app.main import create_app


@dataclass(frozen=True)
class LiveApp:
    app: FastAPI
    base_url: str


class NoopDiscovery:
    def execute(self, run_id: str) -> None:
        del run_id


@pytest.fixture
def live_app(tmp_path) -> Iterator[LiveApp]:
    settings = Settings.load({"LEADGEN_DATABASE_PATH": str(tmp_path / "db.sqlite3")})
    app = create_app(settings)
    app.state.web_run_discovery = NoopDiscovery()
    socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_.bind(("127.0.0.1", 0))
    socket_.listen()
    port = socket_.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = Thread(target=server.run, kwargs={"sockets": [socket_]}, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    deadline = monotonic() + 5
    while monotonic() < deadline:
        try:
            if httpx.get(f"{base_url}/health", timeout=0.2).status_code == 200:
                break
        except httpx.HTTPError:
            sleep(0.05)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("Local test server did not start")

    try:
        yield LiveApp(app=app, base_url=base_url)
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        socket_.close()
