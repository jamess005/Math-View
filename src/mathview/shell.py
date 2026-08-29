"""Native desktop window (QtWebEngine) pointed at the local server."""

from __future__ import annotations

import sys
from pathlib import Path


def open_window(url: str, title: str = "MathView") -> None:
    """Open `url` in a native window; blocks until the window closes."""
    from qtpy.QtCore import QEvent, QTimer, QUrl
    from qtpy.QtGui import QIcon
    from qtpy.QtWebEngineWidgets import (
        QWebEnginePage,  # pyright: ignore[reportAttributeAccessIssue]
        QWebEngineProfile,  # pyright: ignore[reportAttributeAccessIssue]
        QWebEngineView,  # pyright: ignore[reportAttributeAccessIssue]
    )
    from qtpy.QtWidgets import QApplication

    class _View(QWebEngineView):
        """Recovers from the "minimize, then restore" white screen.

        Iconifying on X11 doesn't fire Qt's show/hide events, so QtWebEngine's
        visibility throttling never learns the window came back and leaves the
        last composited frame - often blank - on screen. Toggling page
        visibility off then on, on the real WindowStateChange event, forces a
        fresh compositor frame with no user action needed.
        """

        def changeEvent(self, event) -> None:  # noqa: N802 (Qt override name)
            super().changeEvent(event)
            is_state_change = (
                event.type() == QEvent.WindowStateChange  # pyright: ignore[reportAttributeAccessIssue]
            )
            if is_state_change and not self.isMinimized():
                page = self.page()
                if page is not None:
                    page.setVisible(False)
                    QTimer.singleShot(0, lambda: page.setVisible(True))

    app = QApplication.instance() or QApplication(sys.argv[:1])
    # Set the window's own icon: without _NET_WM_ICON the desktop falls back to
    # a generic one, and every Python app looks alike in the taskbar.
    app.setApplicationName("MathView")
    app.setDesktopFileName("mathview")
    icon = QIcon.fromTheme("mathview")
    if icon.isNull():
        icon = QIcon(str(Path(__file__).resolve().parents[2] / "assets" / "mathview-256.png"))
    app.setWindowIcon(icon)

    view = _View()
    # Off-the-record profile: the default profile's disk cache can be left
    # locked or corrupt by an unclean exit, which shows up as a white window.
    profile = QWebEngineProfile()
    page = QWebEnginePage(profile)
    view.setPage(page)
    view.setWindowTitle(title)
    view.resize(1280, 860)
    view.load(QUrl(url))
    view.show()

    runner = getattr(app, "exec", None) or app.exec_
    runner()

    # Python controls destruction order (page before profile); Qt's
    # parent-child teardown does not guarantee it.
    view.setPage(None)
    del page
    del profile
