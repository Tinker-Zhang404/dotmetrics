from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QGraphicsScene, QGraphicsView


def numpy_to_qimage(image_array: np.ndarray) -> QImage:
    if image_array.ndim == 2:
        height, width = image_array.shape
        bytes_per_line = width
        return QImage(image_array.data, width, height, bytes_per_line, QImage.Format_Grayscale8).copy()

    if image_array.ndim == 3 and image_array.shape[2] == 3:
        rgb = image_array[:, :, ::-1].copy()
        height, width, _channels = rgb.shape
        bytes_per_line = 3 * width
        return QImage(rgb.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()

    raise ValueError(f"Unsupported image shape: {image_array.shape}")


def numpy_to_qpixmap(image_array: np.ndarray) -> QPixmap:
    return QPixmap.fromImage(numpy_to_qimage(image_array))


class ImageView(QGraphicsView):
    imagePressed = Signal(QPointF)
    imageDragged = Signal(QPointF)
    imageReleased = Signal(QPointF)
    contextRequested = Signal(QPointF, QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        self.setBackgroundBrush(QBrush(QColor("#f5f6f8")))
        self.setFrameShape(QFrame.NoFrame)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setDragMode(QGraphicsView.NoDrag)

        self._pixmap_item = None
        self._middle_dragging = False
        self._left_active = False
        self._last_pan_pos = QPoint()

    def _stop_middle_drag(self) -> None:
        if self._middle_dragging:
            self._middle_dragging = False
            self.unsetCursor()

    def has_image(self) -> bool:
        return self._pixmap_item is not None

    def scene_image_rect(self) -> QRectF:
        if self._pixmap_item is None:
            return QRectF()
        return self._pixmap_item.sceneBoundingRect()

    def set_cv_image(self, image_array: np.ndarray, fit: bool = True) -> None:
        pixmap = numpy_to_qpixmap(image_array)
        if self._pixmap_item is None:
            self._pixmap_item = self.scene().addPixmap(pixmap)
            self._pixmap_item.setZValue(0)
        else:
            self._pixmap_item.setPixmap(pixmap)
            self._pixmap_item.setOffset(0, 0)
        self.scene().setSceneRect(QRectF(pixmap.rect()))
        if fit:
            if self.viewport().width() > 1 and self.viewport().height() > 1:
                self.reset_view()
            else:
                QTimer.singleShot(0, self.reset_view)

    def clear_image(self) -> None:
        self.scene().clear()
        self._pixmap_item = None
        self._stop_middle_drag()
        self._left_active = False

    def reset_view(self) -> None:
        if not self._pixmap_item:
            return
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)

    def zoom_in(self) -> None:
        if self.has_image():
            self.scale(1.15, 1.15)

    def zoom_out(self) -> None:
        if self.has_image():
            self.scale(1 / 1.15, 1 / 1.15)

    def image_pos_from_view_pos(self, position: QPoint, clamp: bool = False) -> QPointF | None:
        if self._pixmap_item is None:
            return None
        scene_pos = self.mapToScene(position)
        rect = self.scene_image_rect()
        if clamp:
            x = min(max(scene_pos.x(), rect.left()), rect.right())
            y = min(max(scene_pos.y(), rect.top()), rect.bottom())
            return QPointF(x, y)
        return scene_pos if rect.contains(scene_pos) else None

    def wheelEvent(self, event) -> None:
        if not self.has_image():
            super().wheelEvent(event)
            return
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.has_image():
            self.reset_view()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._middle_dragging = True
            self._last_pan_pos = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            image_pos = self.image_pos_from_view_pos(event.position().toPoint(), clamp=False)
            if image_pos is not None:
                self._left_active = True
                self.imagePressed.emit(image_pos)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._middle_dragging:
            if not (event.buttons() & Qt.MiddleButton):
                self._stop_middle_drag()
                super().mouseMoveEvent(event)
                return
            current_pos = event.position().toPoint()
            delta = current_pos - self._last_pan_pos
            self._last_pan_pos = current_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        if self._left_active and event.buttons() & Qt.LeftButton:
            image_pos = self.image_pos_from_view_pos(event.position().toPoint(), clamp=True)
            if image_pos is not None:
                self.imageDragged.emit(image_pos)
                event.accept()
                return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton:
            self._stop_middle_drag()
            event.accept()
            return

        if event.button() == Qt.LeftButton and self._left_active:
            image_pos = self.image_pos_from_view_pos(event.position().toPoint(), clamp=True)
            self._left_active = False
            if image_pos is not None:
                self.imageReleased.emit(image_pos)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:
        image_pos = self.image_pos_from_view_pos(event.pos(), clamp=False)
        if image_pos is not None:
            self.contextRequested.emit(image_pos, event.globalPos())
            event.accept()
            return
        super().contextMenuEvent(event)
