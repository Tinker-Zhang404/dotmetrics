from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainterPath, QPainterPathStroker
from PySide6.QtWidgets import QGraphicsLineItem


class MeasurementLineItem(QGraphicsLineItem):
    def __init__(self, line_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.line_id = line_id
        self.setData(0, "measurement_line")
        self.setData(1, line_id)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def shape(self) -> QPainterPath:
        path = QPainterPath(self.line().p1())
        path.lineTo(self.line().p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(14.0)
        return stroker.createStroke(path)
