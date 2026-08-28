from __future__ import annotations

import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsSimpleTextItem,
    QInputDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from .graphics_view import ImageView


class CalibrationDialog(QDialog):
    def __init__(self, image_bgr, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scale Calibration")
        self.resize(1000, 760)

        self.image_bgr = image_bgr
        self.points: list[QPointF] = []
        self.point_items: list[QGraphicsEllipseItem] = []
        self.label_items: list[QGraphicsSimpleTextItem] = []
        self.line_item: QGraphicsLineItem | None = None
        self.pixel_length: float | None = None
        self.real_length_nm: float | None = None
        self.calibration_factor: float | None = None

        self.info_label = QLabel(
            "Click the two endpoints of the visible scale bar. Use the mouse wheel to zoom and middle-drag to pan."
        )
        self.info_label.setWordWrap(True)
        self.status_label = QLabel("Scale-bar points: 0/2")

        self.view = ImageView(self)
        self.view.set_cv_image(self.image_bgr, fit=False)
        self.view.imagePressed.connect(self._add_point)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.clear_button = buttons.addButton("Clear Points", QDialogButtonBox.ResetRole)
        self.finish_button = buttons.button(QDialogButtonBox.Ok)
        self.finish_button.setText("Apply Calibration")
        self.finish_button.setEnabled(False)

        buttons.accepted.connect(self._finish_calibration)
        buttons.rejected.connect(self.reject)
        self.clear_button.clicked.connect(self._clear_points)

        layout = QVBoxLayout(self)
        layout.addWidget(self.info_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.view, 1)
        layout.addWidget(buttons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.view.reset_view()

    def _add_point(self, pos: QPointF) -> None:
        if len(self.points) >= 2:
            return

        self.points.append(pos)
        radius = 4
        ellipse = self.view.scene().addEllipse(
            pos.x() - radius,
            pos.y() - radius,
            radius * 2,
            radius * 2,
            QPen(QColor("red")),
        )
        ellipse.setBrush(QColor("red"))
        ellipse.setZValue(50)
        label = self.view.scene().addSimpleText(str(len(self.points)))
        label.setBrush(QColor("red"))
        label.setPos(pos.x() + 8, pos.y() + 8)
        label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        label.setZValue(51)
        self.point_items.append(ellipse)
        self.label_items.append(label)

        if len(self.points) == 2:
            start, end = self.points
            self.line_item = self.view.scene().addLine(start.x(), start.y(), end.x(), end.y(), QPen(QColor("red"), 2))
            self.line_item.setZValue(49)
            self.finish_button.setEnabled(True)

        self.status_label.setText(f"Scale-bar points: {len(self.points)}/2")

    def _clear_points(self) -> None:
        self.points.clear()
        for item in [*self.point_items, *self.label_items]:
            self.view.scene().removeItem(item)
        self.point_items.clear()
        self.label_items.clear()
        if self.line_item is not None:
            self.view.scene().removeItem(self.line_item)
            self.line_item = None
        self.finish_button.setEnabled(False)
        self.status_label.setText("Scale-bar points: 0/2")

    def _finish_calibration(self) -> None:
        if len(self.points) != 2:
            QMessageBox.warning(self, "Scale Calibration", "Select both endpoints of the scale bar.")
            return

        real_length_nm, accepted = QInputDialog.getDouble(
            self,
            "Scale-Bar Length",
            "Enter the scale-bar length (nm):",
            value=100.0,
            minValue=1e-6,
            decimals=6,
        )
        if not accepted:
            return

        start, end = self.points
        pixel_length = math.hypot(end.x() - start.x(), end.y() - start.y())
        if pixel_length <= 0:
            QMessageBox.warning(self, "Scale Calibration", "The selected pixel distance is invalid.")
            return

        self.pixel_length = float(pixel_length)
        self.real_length_nm = float(real_length_nm)
        self.calibration_factor = self.real_length_nm / self.pixel_length
        QMessageBox.information(
            self,
            "Calibration Applied",
            f"Scale bar: {self.pixel_length:.2f} px = {self.real_length_nm:.2f} nm\n"
            f"Scale factor: {self.calibration_factor:.6f} nm/px",
        )
        self.accept()
