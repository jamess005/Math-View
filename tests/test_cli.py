"""The CLI picks a free port and hands it to the right front end."""

from typer.testing import CliRunner

from mathview.cli import app, find_free_port

runner = CliRunner()


def test_find_free_port_returns_a_usable_port():
    port = find_free_port()

    assert 1024 < port < 65536


def test_web_mode_starts_the_server_without_a_window(monkeypatch):
    started: dict[str, object] = {}
    monkeypatch.setattr(
        "mathview.cli.serve_forever", lambda port: started.update(port=port)
    )

    result = runner.invoke(app, ["--web"])

    assert result.exit_code == 0
    assert "port" in started
