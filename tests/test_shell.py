"""The Qt window's minimize/restore white-screen fix.

Runs against the offscreen QPA platform so it needs no real display. Patches
QApplication.exec to drive one minimize -> restore cycle and return instead of
blocking, and spies on QWebEnginePage.setVisible to confirm open_window()
toggles it off then on across that cycle.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

pytest.importorskip("qtpy")

from qtpy.QtCore import Qt  # noqa: E402
from qtpy.QtWebEngineWidgets import QWebEnginePage  # noqa: E402
from qtpy.QtWidgets import QApplication  # noqa: E402

from mathview.shell import open_window  # noqa: E402


@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="QtWebEngine (Chromium) aborts on display-less CI runners",
)
def test_minimize_then_restore_toggles_page_visibility(monkeypatch):
    calls: list[bool] = []
    monkeypatch.setattr(
        QWebEnginePage, "setVisible", lambda self, visible: calls.append(visible)
    )

    def fake_exec(self):
        window = next(w for w in QApplication.topLevelWidgets() if w.isVisible())
        window.setWindowState(Qt.WindowMinimized)
        window.setWindowState(Qt.WindowNoState)
        QApplication.processEvents()
        return 0

    monkeypatch.setattr(QApplication, "exec_", fake_exec, raising=False)
    monkeypatch.setattr(QApplication, "exec", fake_exec, raising=False)

    open_window("http://127.0.0.1:1/")

    assert False in calls and True in calls
