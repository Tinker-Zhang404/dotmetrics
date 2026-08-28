from __future__ import annotations

import sys
import traceback

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen


APP_STYLESHEET = """
QWidget {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    color: #111827;
}
QMainWindow, QTabWidget::pane, QPlainTextEdit, QGroupBox, QGraphicsView {
    background: #f3f4f6;
}
QGroupBox {
    border: 1px solid #d1d5db;
    border-radius: 10px;
    margin-top: 8px;
    padding-top: 10px;
    background: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #374151;
    font-weight: 600;
    font-size: 15px;
}
#leftPanel {
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 4px;
}
#leftPanel QGroupBox {
    background: #ffffff;
    border: 1px solid #d1d5db;
}
#leftPanel QPushButton {
    background: #f3f4f6;
    color: #111827;
    border: 1px solid #c7ccd4;
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 22px;
}
#controlScroll {
    border: none;
    background: transparent;
}
#leftPanel QLabel, #leftPanel QCheckBox, #leftPanel QRadioButton {
    padding: 0;
}
#leftPanel QCheckBox::indicator, #leftPanel QRadioButton::indicator {
    width: 16px;
    height: 16px;
}
#leftPanel QPushButton:hover {
    background: #e5e7eb;
}
#leftPanel QPushButton:pressed {
    background: #d1d5db;
}
#leftPanel QPushButton:disabled {
    background: #eef0f3;
    color: #9ca3af;
    border: 1px solid #e2e5ea;
}
#leftPanel QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #d1d5db;
    border-radius: 3px;
}
#leftPanel QSlider::handle:horizontal {
    background: #6b7280;
    border: none;
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
#leftPanel QProgressBar {
    border: 1px solid #bcc3cc;
    border-radius: 9px;
    text-align: center;
    background: #e9edf1;
    color: #374151;
    font-weight: 600;
    min-height: 20px;
    padding: 1px;
}
#leftPanel QProgressBar::chunk {
    border-radius: 8px;
    margin: 1px;
    background: qlineargradient(
        x1: 0,
        y1: 0,
        x2: 1,
        y2: 0,
        stop: 0 #9aa3af,
        stop: 1 #6b7280
    );
}
QPlainTextEdit, QGraphicsView {
    border: 1px solid #d1d5db;
    border-radius: 10px;
    background: #ffffff;
}
QScrollBar:vertical {
    background: #e5e7eb;
    width: 14px;
    margin: 0;
    border: 1px solid #cfd4dc;
    border-radius: 7px;
}
QScrollBar::handle:vertical {
    background: #9ca3af;
    min-height: 28px;
    border-radius: 6px;
}
QScrollBar::handle:vertical:hover {
    background: #6b7280;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: #e5e7eb;
    height: 14px;
    margin: 0;
    border: 1px solid #cfd4dc;
    border-radius: 7px;
}
QScrollBar::handle:horizontal {
    background: #9ca3af;
    min-width: 28px;
    border-radius: 6px;
}
QScrollBar::handle:horizontal:hover {
    background: #6b7280;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}
"""


def _create_splash() -> QSplashScreen:
    pixmap = QPixmap(560, 300)
    pixmap.fill(QColor("#f3f4f6"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QColor("#d1d5db"))
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(20, 20, 520, 260, 16, 16)

    painter.setPen(QColor("#111827"))
    painter.setFont(QFont("Segoe UI", 20, QFont.DemiBold))
    painter.drawText(44, 120, "DotMetrics")

    painter.setPen(QColor("#4b5563"))
    painter.setFont(QFont("Segoe UI", 11))
    painter.drawText(44, 156, "Automated TEM particle measurement")
    painter.end()

    splash = QSplashScreen(pixmap)
    splash.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    splash.showMessage("Starting...", Qt.AlignHCenter | Qt.AlignBottom, QColor("#6b7280"))
    return splash


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("DotMetrics")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    splash = _create_splash()
    splash.show()
    app.processEvents()

    try:
        splash.showMessage("Loading interface...", Qt.AlignHCenter | Qt.AlignBottom, QColor("#6b7280"))
        app.processEvents()

        from .ui.main_window import MainWindow

        splash.showMessage("Preparing workspace...", Qt.AlignHCenter | Qt.AlignBottom, QColor("#6b7280"))
        app.processEvents()

        window = MainWindow()
        window.show()
        splash.finish(window)
        return app.exec()
    except Exception as exc:
        traceback.print_exc()
        splash.close()
        QMessageBox.critical(None, "Application Error", str(exc))
        return 1
