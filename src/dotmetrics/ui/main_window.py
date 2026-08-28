from __future__ import annotations

import math
import traceback
from pathlib import Path

import cv2
from PySide6.QtCore import QObject, QPointF, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QColor, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFileDialog,
    QDialog,
    QFormLayout,
    QGraphicsItem,
    QGraphicsSimpleTextItem,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)

from ..core import ImageLoader, ParticleAnalyzer, ResultExporter, logger, temp_dir
from ..domain import AnalysisResult, DetectionSettings, MeasurementLine, Particle
from .calibration_dialog import CalibrationDialog
from .graphics_view import ImageView
from .log_handler import QtLogHandler
from .scene_items import MeasurementLineItem


class AnalysisWorker(QObject):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int, str)

    def __init__(self, analyzer: ParticleAnalyzer, image_bgr, calibration_factor: float, settings: DetectionSettings):
        super().__init__()
        self.analyzer = analyzer
        self.image_bgr = image_bgr
        self.calibration_factor = calibration_factor
        self.settings = settings

    @Slot()
    def run(self) -> None:
        try:
            self.progress.emit(15, "Running particle analysis...")
            result = self.analyzer.analyze(self.image_bgr, self.calibration_factor, self.settings)
            self.progress.emit(90, "Analysis complete. Updating the interface...")
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class ModelLoadWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, analyzer: ParticleAnalyzer):
        super().__init__()
        self.analyzer = analyzer

    @Slot()
    def run(self) -> None:
        try:
            ready = self.analyzer.initialize_model()
            message = "Detector ready" if ready else "Detector could not be loaded"
            self.finished.emit(ready, message)
        except Exception as exc:
            self.finished.emit(False, str(exc))


class MainWindow(QMainWindow):
    def __init__(self, preload_model: bool = True) -> None:
        super().__init__()
        self.setWindowTitle("DotMetrics v1.0.0")
        self.resize(1500, 920)

        self.logger = logger
        self.analyzer = ParticleAnalyzer()
        self.exporter = ResultExporter()

        self.current_image_path: Path | None = None
        self.current_image_bgr = None
        self.current_result: AnalysisResult | None = None
        self.calibration_factor = 1.0
        self.is_calibrated = False
        self.selected_particles: set[int] = set()
        self.filtered_particles: set[int] = set()
        self.measurement_lines: list[MeasurementLine] = []
        self.next_measurement_line_id = 1
        self.model_ready = False

        self.overlay_items: list[QGraphicsItem] = []
        self.temp_line_item = None
        self.temp_line_halo_item = None
        self.drawing_start: QPointF | None = None

        self.analysis_thread: QThread | None = None
        self.analysis_worker: AnalysisWorker | None = None
        self.model_thread: QThread | None = None
        self.model_worker: ModelLoadWorker | None = None

        self.histogram_temp_path = temp_dir() / "histogram.png"
        self.stats_temp_path = temp_dir() / "stats.png"

        self._build_ui()
        self._attach_log_handler()
        self._update_detection_labels()
        self._update_particle_status()
        self._update_draw_status()
        self._update_action_states()
        self.statusBar().showMessage("Mouse wheel: zoom | Double-click: reset | Middle-drag: pan")
        self.log("DotMetrics started")
        if preload_model:
            self._start_model_preload()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        left_panel = QWidget(self)
        left_panel.setObjectName("leftPanel")
        left_panel.setMinimumWidth(390)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        left_layout.setSizeConstraint(QLayout.SetMinimumSize)
        self.left_scroll = QScrollArea(self)
        self.left_scroll.setObjectName("controlScroll")
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setFixedWidth(420)
        self.left_scroll.setWidget(left_panel)
        root_layout.addWidget(self.left_scroll)

        project_group = QGroupBox("Image Analysis")
        project_layout = QVBoxLayout(project_group)
        self.load_button = QPushButton("Open TEM Image")
        self.load_button.clicked.connect(self.load_image)
        self.model_status_label = QLabel("Detector: loading...")
        self.model_status_label.setWordWrap(True)
        self.calibrate_button = QPushButton("Calibrate Scale")
        self.calibrate_button.clicked.connect(self.open_calibration)
        self.calibration_label = QLabel("Scale: not calibrated")
        self.calibration_label.setWordWrap(True)
        self.analyze_button = QPushButton("Run Analysis")
        self.analyze_button.clicked.connect(self.start_analysis)
        self.save_button = QPushButton("Export Results")
        self.save_button.clicked.connect(self.save_results)
        project_layout.addWidget(self.load_button)
        project_layout.addWidget(self.model_status_label)
        project_layout.addWidget(self.calibrate_button)
        project_layout.addWidget(self.calibration_label)
        project_layout.addWidget(self.analyze_button)
        project_layout.addWidget(self.save_button)
        left_layout.addWidget(project_group)

        settings_group = QGroupBox("Detection Settings")
        settings_layout = QFormLayout(settings_group)
        self.conf_slider = self._create_slider(1, 99, 10)
        self.conf_value_label = QLabel()
        self.iou_slider = self._create_slider(5, 95, 30)
        self.iou_value_label = QLabel()
        settings_layout.addRow("Confidence", self._make_slider_row(self.conf_slider, self.conf_value_label))
        settings_layout.addRow("IoU", self._make_slider_row(self.iou_slider, self.iou_value_label))
        left_layout.addWidget(settings_group)
        manual_group = QGroupBox("Review and Manual Measurement")
        manual_layout = QVBoxLayout(manual_group)
        self.draw_mode_checkbox = QCheckBox("Draw Manual Diameter Lines")
        self.draw_mode_checkbox.toggled.connect(self._on_draw_mode_changed)
        self.draw_status_label = QLabel()
        self.clear_draw_button = QPushButton("Clear Manual Lines")
        self.clear_draw_button.clicked.connect(lambda: self._clear_measurements(log_action=True))
        self.draw_stats_label = QLabel()
        self.select_mode_radio = QRadioButton("Selection Mode")
        self.select_mode_radio.setChecked(True)
        self.select_mode_radio.toggled.connect(self._update_selection_mode_log)
        self.filter_mode_radio = QRadioButton("Exclusion Mode")
        self.filter_mode_radio.toggled.connect(self._update_selection_mode_log)
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self.select_all_particles)
        self.deselect_all_button = QPushButton("Clear Selection")
        self.deselect_all_button.clicked.connect(self.deselect_all_particles)
        self.delete_selected_button = QPushButton("Exclude Selected")
        self.delete_selected_button.clicked.connect(self.delete_selected_particles)
        self.restore_all_button = QPushButton("Restore Excluded")
        self.restore_all_button.clicked.connect(self.restore_all_particles)
        self.particle_status_label = QLabel()
        manual_layout.addWidget(self.draw_mode_checkbox)
        manual_layout.addWidget(self.draw_status_label)
        manual_layout.addWidget(self.clear_draw_button)
        manual_layout.addWidget(self.draw_stats_label)
        manual_layout.addWidget(self.select_mode_radio)
        manual_layout.addWidget(self.filter_mode_radio)
        manual_layout.addWidget(self.select_all_button)
        manual_layout.addWidget(self.deselect_all_button)
        manual_layout.addWidget(self.delete_selected_button)
        manual_layout.addWidget(self.restore_all_button)
        manual_layout.addWidget(self.particle_status_label)
        left_layout.addWidget(manual_group)

        zoom_group = QGroupBox("View")
        zoom_layout = QHBoxLayout(zoom_group)
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.clicked.connect(lambda: self._zoom_active_view("in"))
        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.clicked.connect(lambda: self._zoom_active_view("out"))
        self.zoom_reset_button = QPushButton("Fit to Window")
        self.zoom_reset_button.clicked.connect(lambda: self._zoom_active_view("reset"))
        zoom_layout.addWidget(self.zoom_in_button)
        zoom_layout.addWidget(self.zoom_out_button)
        zoom_layout.addWidget(self.zoom_reset_button)
        left_layout.addWidget(zoom_group)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        left_layout.addWidget(self.progress_bar)

        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QPlainTextEdit(self)
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        left_layout.addWidget(log_group, 1)

        for button in left_panel.findChildren(QPushButton):
            readable_height = button.fontMetrics().height() + 16
            button.setMinimumHeight(max(36, readable_height))

        self.tabs = QTabWidget(self)
        self.original_view = ImageView(self)
        self.result_view = ImageView(self)
        self.hist_view = ImageView(self)
        self.stats_view = ImageView(self)
        self.result_view.imagePressed.connect(self._on_result_image_pressed)
        self.result_view.imageDragged.connect(self._on_result_image_dragged)
        self.result_view.imageReleased.connect(self._on_result_image_released)
        self.result_view.contextRequested.connect(self._show_result_context_menu)
        self.tabs.addTab(self.original_view, "Original Image")
        self.tabs.addTab(self.result_view, "Analysis Results")
        self.tabs.addTab(self.hist_view, "Size Distribution")
        self.tabs.addTab(self.stats_view, "Summary Statistics")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        root_layout.addWidget(self.tabs, 1)

    def _create_slider(self, minimum: int, maximum: int, value: int) -> QSlider:
        slider = QSlider(Qt.Horizontal, self)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        slider.valueChanged.connect(self._update_detection_labels)
        return slider

    def _make_slider_row(self, slider: QSlider, value_label: QLabel) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(slider, 1)
        layout.addWidget(value_label)
        return row

    def _attach_log_handler(self) -> None:
        self.qt_log_handler = QtLogHandler()
        self.qt_log_handler.setFormatter(self.logger.handlers[0].formatter)
        self.qt_log_handler.message_emitted.connect(self._append_log_line)
        self.logger.addHandler(self.qt_log_handler)

    def _append_log_line(self, text: str) -> None:
        self.log_text.appendPlainText(text)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def log(self, message: str) -> None:
        self.logger.info(message)

    def _settings_from_ui(self) -> DetectionSettings:
        return DetectionSettings(
            conf=self.conf_slider.value() / 100,
            iou=self.iou_slider.value() / 100,
            max_det=2000,
        )

    def _update_detection_labels(self, _value: int | None = None) -> None:
        self.conf_value_label.setText(f"{self.conf_slider.value() / 100:.2f}")
        self.iou_value_label.setText(f"{self.iou_slider.value() / 100:.2f}")

    def _analysis_running(self) -> bool:
        return self.analysis_thread is not None and self.analysis_thread.isRunning()

    def _start_model_preload(self) -> None:
        if self.model_thread is not None and self.model_thread.isRunning():
            return
        self.model_status_label.setText("Detector: loading in background...")
        self.log("Preloading the detector in the background")
        self.model_thread = QThread(self)
        self.model_worker = ModelLoadWorker(self.analyzer)
        self.model_worker.moveToThread(self.model_thread)
        self.model_thread.started.connect(self.model_worker.run)
        self.model_worker.finished.connect(self._on_model_preload_finished)
        self.model_worker.finished.connect(self.model_thread.quit)
        self.model_thread.finished.connect(self._cleanup_model_thread)
        self.model_thread.start()

    @Slot(bool, str)
    def _on_model_preload_finished(self, ready: bool, message: str) -> None:
        self.model_ready = ready
        self.model_status_label.setText("Detector: ready" if ready else "Detector: unavailable")
        self.log(message)
        self._update_action_states()

    @Slot()
    def _cleanup_model_thread(self) -> None:
        if self.model_worker is not None:
            self.model_worker.deleteLater()
            self.model_worker = None
        if self.model_thread is not None:
            self.model_thread.deleteLater()
            self.model_thread = None

    def _update_action_states(self) -> None:
        has_image = self.current_image_bgr is not None
        has_result = self.current_result is not None
        running = self._analysis_running()
        self.analyze_button.setEnabled(has_image and self.is_calibrated and self.model_ready and not running)
        self.calibrate_button.setEnabled(has_image and not running)
        self.save_button.setEnabled(has_result and not running)
        self.select_all_button.setEnabled(has_result and not running)
        self.deselect_all_button.setEnabled(has_result and not running)
        self.delete_selected_button.setEnabled(has_result and bool(self.selected_particles) and not running)
        self.restore_all_button.setEnabled(has_result and bool(self.filtered_particles) and not running)
        self.draw_mode_checkbox.setEnabled(has_result and not running)
        self.clear_draw_button.setEnabled(has_result and bool(self.measurement_lines) and not running)
        self.zoom_in_button.setEnabled(has_image)
        self.zoom_out_button.setEnabled(has_image)
        self.zoom_reset_button.setEnabled(has_image)

    def _update_particle_status(self) -> None:
        if self.current_result is None:
            self.particle_status_label.setText("Particles: 0 | Selected: 0 | Excluded: 0")
            return
        self.particle_status_label.setText(
            f"Particles: {len(self.current_result.particles)} | Selected: {len(self.selected_particles)} | "
            f"Excluded: {len(self.filtered_particles)}"
        )

    def _update_draw_status(self) -> None:
        draw_mode = self.draw_mode_checkbox.isChecked()
        self.draw_status_label.setText(f"Manual drawing: {'on' if draw_mode else 'off'}")
        self.draw_stats_label.setText(f"Manual lines: {len(self.measurement_lines)}")

    def _update_selection_mode_log(self, _checked: bool = False) -> None:
        if self.select_mode_radio.isChecked():
            self.log("Selection mode: click a particle to toggle its selection")
        elif self.filter_mode_radio.isChecked():
            self.log("Exclusion mode: click a particle to exclude it")

    def _on_draw_mode_changed(self, _checked: bool = False) -> None:
        self._update_draw_status()
        self.log("Manual diameter drawing enabled" if self.draw_mode_checkbox.isChecked() else "Manual diameter drawing disabled")

    def load_image(self) -> None:
        if self._analysis_running():
            QMessageBox.warning(self, "Analysis in Progress", "Wait for the current analysis before opening another image.")
            return

        file_path, _filter = QFileDialog.getOpenFileName(
            self,
            "Open TEM Image",
            "",
            "Image Files (*.jpg *.jpeg *.png *.tif *.tiff *.bmp)",
        )
        if not file_path:
            return

        image_bgr, _scale = ImageLoader.load_image(file_path)
        if image_bgr is None:
            QMessageBox.critical(self, "Image Load Failed", f"The image could not be loaded:\n{file_path}")
            return

        self._reset_for_new_image()
        self.current_image_path = Path(file_path)
        self.current_image_bgr = image_bgr
        self.original_view.set_cv_image(image_bgr, fit=True)
        self.result_view.set_cv_image(image_bgr, fit=True)
        self.tabs.setCurrentWidget(self.original_view)
        self.log(f"Loaded image: {self.current_image_path.name} ({image_bgr.shape[1]} x {image_bgr.shape[0]})")
        self._update_action_states()

    def _reset_for_new_image(self) -> None:
        self.current_result = None
        self.selected_particles.clear()
        self.filtered_particles.clear()
        self.measurement_lines.clear()
        self.next_measurement_line_id = 1
        self.drawing_start = None
        self.is_calibrated = False
        self.calibration_factor = 1.0
        self.calibration_label.setText("Scale: not calibrated")
        self._clear_overlay_items()
        self._clear_temp_line_item()
        self.hist_view.clear_image()
        self.stats_view.clear_image()
        self.progress_bar.setValue(0)
        self._update_particle_status()
        self._update_draw_status()

    def open_calibration(self) -> None:
        if self.current_image_bgr is None:
            QMessageBox.warning(self, "Scale Calibration", "Open an image before calibrating its scale.")
            return

        dialog = CalibrationDialog(self.current_image_bgr, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.calibration_factor is not None:
            self.calibration_factor = dialog.calibration_factor
            self.is_calibrated = True
            self.calibration_label.setText(f"Scale: {self.calibration_factor:.6f} nm/px")
            self.log(
                f"Scale calibrated: {dialog.pixel_length:.2f} px = {dialog.real_length_nm:.2f} nm; "
                f"scale factor = {self.calibration_factor:.6f} nm/px"
            )
            self._update_action_states()

    def start_analysis(self) -> None:
        if self.current_image_bgr is None:
            QMessageBox.warning(self, "Analysis", "Open an image before running the analysis.")
            return
        if not self.is_calibrated:
            QMessageBox.warning(self, "Analysis", "Calibrate the image scale before running the analysis.")
            return
        if not self.model_ready:
            QMessageBox.warning(self, "Analysis", "The detector is still loading or is unavailable.")
            return
        if self._analysis_running():
            QMessageBox.warning(self, "Analysis", "An analysis is already running.")
            return

        self.current_result = None
        self.selected_particles.clear()
        self.filtered_particles.clear()
        self.measurement_lines.clear()
        self.next_measurement_line_id = 1
        self._clear_overlay_items()
        self._clear_temp_line_item()
        self._update_particle_status()
        self._update_draw_status()
        self._update_action_states()

        settings = self._settings_from_ui().clamped()
        calibration_factor = self.calibration_factor if self.is_calibrated else 1.0
        self.progress_bar.setValue(5)
        self.log(
            f"Starting analysis: confidence={settings.conf:.2f}, IoU={settings.iou:.2f}, "
            f"max detections={settings.max_det}, scale={calibration_factor:.6f} nm/px"
        )

        self.analysis_thread = QThread(self)
        self.analysis_worker = AnalysisWorker(self.analyzer, self.current_image_bgr.copy(), calibration_factor, settings)
        self.analysis_worker.moveToThread(self.analysis_thread)
        self.analysis_thread.started.connect(self.analysis_worker.run)
        self.analysis_worker.progress.connect(self._on_analysis_progress)
        self.analysis_worker.finished.connect(self._on_analysis_finished)
        self.analysis_worker.error.connect(self._on_analysis_error)
        self.analysis_worker.finished.connect(self.analysis_thread.quit)
        self.analysis_worker.error.connect(self.analysis_thread.quit)
        self.analysis_thread.finished.connect(self._cleanup_analysis_thread)
        self.analysis_thread.start()
        self._update_action_states()

    @Slot(int, str)
    def _on_analysis_progress(self, value: int, message: str) -> None:
        self.progress_bar.setValue(value)
        self.log(message)

    @Slot(object)
    def _on_analysis_finished(self, result: AnalysisResult) -> None:
        self.current_result = result
        self.progress_bar.setValue(100)
        if self.current_image_bgr is not None:
            self.result_view.set_cv_image(self.current_image_bgr, fit=True)
        self._rebuild_result_overlays()
        self._update_particle_status()
        self._update_draw_status()
        self._update_plots()
        self._update_action_states()
        self.tabs.setCurrentWidget(self.result_view)
        QTimer.singleShot(0, self.result_view.reset_view)
        measurements = self.current_result.particle_measurements(self.filtered_particles)
        if measurements:
            self.log(
                f"Analysis complete: {len(self.current_result.particles)} particles detected; "
                f"mean diameter = {sum(measurements) / len(measurements):.2f} nm"
            )
        else:
            self.log("Analysis complete: no particles detected")

    @Slot(str)
    def _on_analysis_error(self, message: str) -> None:
        self.progress_bar.setValue(0)
        self._update_action_states()
        self.log(f"Analysis failed: {message}")
        QMessageBox.critical(self, "Analysis Failed", message)

    @Slot()
    def _cleanup_analysis_thread(self) -> None:
        if self.analysis_worker is not None:
            self.analysis_worker.deleteLater()
            self.analysis_worker = None
        if self.analysis_thread is not None:
            self.analysis_thread.deleteLater()
            self.analysis_thread = None
        self._update_action_states()
    def _on_result_image_pressed(self, pos: QPointF) -> None:
        if self.current_result is None:
            return
        if self.draw_mode_checkbox.isChecked():
            self.drawing_start = pos
            self._clear_temp_line_item()
            scene = self.result_view.scene()
            halo_pen = QPen(QColor(17, 24, 39, 140), 6, Qt.DashLine)
            halo_pen.setCosmetic(True)
            self.temp_line_halo_item = scene.addLine(pos.x(), pos.y(), pos.x(), pos.y(), halo_pen)
            self.temp_line_halo_item.setZValue(100)
            pen = QPen(QColor("#ef4444"), 3, Qt.DashLine)
            pen.setCosmetic(True)
            self.temp_line_item = scene.addLine(pos.x(), pos.y(), pos.x(), pos.y(), pen)
            self.temp_line_item.setZValue(101)
            return
        self._handle_particle_click(pos)

    def _on_result_image_dragged(self, pos: QPointF) -> None:
        if self.drawing_start is None:
            return
        if self.temp_line_halo_item is not None:
            self.temp_line_halo_item.setLine(self.drawing_start.x(), self.drawing_start.y(), pos.x(), pos.y())
        if self.temp_line_item is not None:
            self.temp_line_item.setLine(self.drawing_start.x(), self.drawing_start.y(), pos.x(), pos.y())

    def _on_result_image_released(self, pos: QPointF) -> None:
        if self.drawing_start is None:
            return
        start = self.drawing_start
        self.drawing_start = None
        self._clear_temp_line_item()

        line_length_px = math.hypot(pos.x() - start.x(), pos.y() - start.y())
        if line_length_px <= 2:
            return

        diameter_nm = line_length_px * self.calibration_factor
        measurement_line = MeasurementLine(
            id=self.next_measurement_line_id,
            start_px=(start.x(), start.y()),
            end_px=(pos.x(), pos.y()),
            diameter_nm=diameter_nm,
        )
        self.next_measurement_line_id += 1
        self.measurement_lines.append(measurement_line)
        self.log(f"Added manual diameter line #{measurement_line.id}: {measurement_line.diameter_nm:.1f} nm")
        self._update_draw_status()
        self._rebuild_result_overlays()
        self._update_plots()
        self._update_action_states()

    def _clear_temp_line_item(self) -> None:
        if self.temp_line_item is not None:
            self.result_view.scene().removeItem(self.temp_line_item)
            self.temp_line_item = None
        if self.temp_line_halo_item is not None:
            self.result_view.scene().removeItem(self.temp_line_halo_item)
            self.temp_line_halo_item = None

    def _handle_particle_click(self, pos: QPointF) -> None:
        particle = self._find_particle_at(pos)
        if particle is None:
            return
        if particle.id in self.filtered_particles and self.select_mode_radio.isChecked():
            return

        if self.select_mode_radio.isChecked():
            if particle.id in self.selected_particles:
                self.selected_particles.remove(particle.id)
            else:
                self.selected_particles.add(particle.id)
        else:
            if particle.id not in self.filtered_particles:
                self.filtered_particles.add(particle.id)
                self.selected_particles.discard(particle.id)
                self._update_plots()

        self._rebuild_result_overlays()
        self._update_particle_status()
        self._update_action_states()

    def _find_particle_at(self, pos: QPointF) -> Particle | None:
        if self.current_result is None:
            return None
        candidates = [particle for particle in self.current_result.particles if particle.contains(pos.x(), pos.y())]
        if not candidates:
            return None
        return min(candidates, key=lambda particle: particle.area_hint)

    def _find_measurement_line_at(self, pos: QPointF) -> MeasurementLine | None:
        best_line = None
        best_distance = 8.0
        for line in self.measurement_lines:
            distance = self._distance_to_segment(pos, line)
            if distance <= best_distance:
                best_distance = distance
                best_line = line
        return best_line

    def _distance_to_segment(self, pos: QPointF, line: MeasurementLine) -> float:
        px, py = pos.x(), pos.y()
        x1, y1 = line.start_px
        x2, y2 = line.end_px
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy
        return math.hypot(px - nearest_x, py - nearest_y)

    def _show_result_context_menu(self, pos: QPointF, global_pos) -> None:
        if self.current_result is None or self.drawing_start is not None:
            return

        line = self._find_measurement_line_at(pos)
        particle = self._find_particle_at(pos)
        menu = QMenu(self)
        delete_action = None
        restore_action = None

        if line is not None:
            delete_action = QAction("Delete Manual Line", self)
            menu.addAction(delete_action)
        if particle is not None and particle.id in self.filtered_particles:
            restore_action = QAction("Restore Particle", self)
            menu.addAction(restore_action)
        if menu.isEmpty():
            return

        chosen = menu.exec(global_pos)
        if chosen == delete_action and line is not None:
            self._remove_measurement_line(line.id)
        elif chosen == restore_action and particle is not None:
            self._restore_particle(particle.id)

    def _remove_measurement_line(self, line_id: int) -> None:
        before = len(self.measurement_lines)
        self.measurement_lines = [line for line in self.measurement_lines if line.id != line_id]
        if len(self.measurement_lines) == before:
            return
        self.log(f"Deleted manual diameter line #{line_id}")
        self._update_draw_status()
        self._rebuild_result_overlays()
        self._update_plots()
        self._update_action_states()

    def _restore_particle(self, particle_id: int) -> None:
        if particle_id not in self.filtered_particles:
            return
        self.filtered_particles.remove(particle_id)
        self.log(f"Restored particle #{particle_id}")
        self._rebuild_result_overlays()
        self._update_particle_status()
        self._update_plots()
        self._update_action_states()

    def _clear_measurements(self, log_action: bool = False) -> None:
        if not self.measurement_lines and self.temp_line_item is None and self.temp_line_halo_item is None:
            return
        self.measurement_lines.clear()
        self.next_measurement_line_id = 1
        self._clear_temp_line_item()
        self._update_draw_status()
        self._rebuild_result_overlays()
        self._update_plots()
        self._update_action_states()
        if log_action:
            self.log("Cleared all manual diameter lines")

    def _clear_overlay_items(self) -> None:
        for item in self.overlay_items:
            self.result_view.scene().removeItem(item)
        self.overlay_items.clear()

    def _rebuild_result_overlays(self) -> None:
        self._clear_overlay_items()
        if self.current_result is None or self.current_image_bgr is None:
            return

        scene = self.result_view.scene()
        for particle in self.current_result.particles:
            path = self._build_contour_path(particle.contour)
            halo_item = scene.addPath(path, self._particle_halo_pen(particle.id))
            halo_item.setZValue(9)
            self.overlay_items.append(halo_item)
            path_item = scene.addPath(path, self._particle_pen(particle.id))
            path_item.setZValue(10)
            self.overlay_items.append(path_item)

            x1, y1, _x2, _y2 = particle.bbox
            label_text = f"{particle.diameter_nm:.1f}nm"
            if particle.id in self.filtered_particles:
                label_text = f"X {label_text}"
                brush_color = QColor("#4b5563")
            elif particle.id in self.selected_particles:
                label_text = f"* {label_text}"
                brush_color = QColor("#991b1b")
            else:
                brush_color = QColor("#111827")

            label = QGraphicsSimpleTextItem(label_text)
            label.setBrush(brush_color)
            label.setPos(float(x1), float(max(y1 - 12, 0)))
            label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            label.setZValue(11)
            scene.addItem(label)
            self.overlay_items.append(label)

        for line in self.measurement_lines:
            halo_item = scene.addLine(line.start_px[0], line.start_px[1], line.end_px[0], line.end_px[1])
            halo_pen = QPen(QColor(17, 24, 39, 155), 6)
            halo_pen.setCosmetic(True)
            halo_item.setPen(halo_pen)
            halo_item.setZValue(20)
            scene.addItem(halo_item)
            self.overlay_items.append(halo_item)

            line_item = MeasurementLineItem(
                line.id,
                line.start_px[0],
                line.start_px[1],
                line.end_px[0],
                line.end_px[1],
            )
            pen = QPen(QColor("#ef4444"), 3)
            pen.setCosmetic(True)
            line_item.setPen(pen)
            line_item.setZValue(21)
            scene.addItem(line_item)
            self.overlay_items.append(line_item)

            label = QGraphicsSimpleTextItem(f"{line.diameter_nm:.1f}nm")
            label.setBrush(QColor("#b91c1c"))
            label.setPos(
                (line.start_px[0] + line.end_px[0]) / 2,
                max((line.start_px[1] + line.end_px[1]) / 2 - 12, 0),
            )
            label.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            label.setZValue(22)
            scene.addItem(label)
            self.overlay_items.append(label)

    def _build_contour_path(self, contour) -> QPainterPath:
        points = contour.reshape(-1, 2)
        path = QPainterPath(QPointF(float(points[0][0]), float(points[0][1])))
        for x_coord, y_coord in points[1:]:
            path.lineTo(float(x_coord), float(y_coord))
        path.closeSubpath()
        return path

    def _particle_pen(self, particle_id: int) -> QPen:
        if particle_id in self.filtered_particles:
            pen = QPen(QColor("#6b7280"), 2, Qt.DashLine)
        elif particle_id in self.selected_particles:
            pen = QPen(QColor("#dc2626"), 3)
        else:
            pen = QPen(QColor("#22c55e"), 2)
        pen.setCosmetic(True)
        return pen

    def _particle_halo_pen(self, particle_id: int) -> QPen:
        if particle_id in self.filtered_particles:
            pen = QPen(QColor(17, 24, 39, 120), 4, Qt.DashLine)
        elif particle_id in self.selected_particles:
            pen = QPen(QColor(17, 24, 39, 145), 5)
        else:
            pen = QPen(QColor(17, 24, 39, 120), 4)
        pen.setCosmetic(True)
        return pen
    def _update_plots(self) -> None:
        if self.current_result is None:
            self.hist_view.clear_image()
            self.stats_view.clear_image()
            return
        measurements = self.current_result.combined_measurements(self.filtered_particles, self.measurement_lines)
        from ..core import Visualizer

        Visualizer.create_histogram(measurements, self.histogram_temp_path)
        Visualizer.create_stats_table(measurements, self.stats_temp_path)

        histogram = cv2.imread(str(self.histogram_temp_path))
        stats = cv2.imread(str(self.stats_temp_path))
        if histogram is not None:
            self.hist_view.set_cv_image(histogram, fit=True)
            QTimer.singleShot(0, self.hist_view.reset_view)
        if stats is not None:
            self.stats_view.set_cv_image(stats, fit=True)
            QTimer.singleShot(0, self.stats_view.reset_view)

    def select_all_particles(self) -> None:
        if self.current_result is None:
            return
        self.selected_particles = {particle.id for particle in self.current_result.particles if particle.id not in self.filtered_particles}
        self.log(f"Selected {len(self.selected_particles)} particles")
        self._rebuild_result_overlays()
        self._update_particle_status()
        self._update_action_states()

    def deselect_all_particles(self) -> None:
        self.selected_particles.clear()
        self.log("Cleared the particle selection")
        self._rebuild_result_overlays()
        self._update_particle_status()
        self._update_action_states()

    def delete_selected_particles(self) -> None:
        if not self.selected_particles:
            QMessageBox.information(self, "Exclude Particles", "No particles are selected.")
            return
        self.filtered_particles.update(self.selected_particles)
        removed_count = len(self.selected_particles)
        self.selected_particles.clear()
        self.log(f"Excluded {removed_count} particles")
        self._rebuild_result_overlays()
        self._update_particle_status()
        self._update_plots()
        self._update_action_states()

    def restore_all_particles(self) -> None:
        if not self.filtered_particles:
            QMessageBox.information(self, "Restore Particles", "There are no excluded particles to restore.")
            return
        self.filtered_particles.clear()
        self.log("Restored all excluded particles")
        self._rebuild_result_overlays()
        self._update_particle_status()
        self._update_plots()
        self._update_action_states()

    def save_results(self) -> None:
        if self.current_result is None or self.current_image_bgr is None:
            QMessageBox.warning(self, "Export Results", "There are no analysis results to export.")
            return

        directory = QFileDialog.getExistingDirectory(self, "Choose Export Folder")
        if not directory:
            return

        try:
            output_dir = self.exporter.export(
                directory,
                self.current_image_path,
                self.current_image_bgr,
                self.calibration_factor,
                self.is_calibrated,
                self.current_result,
                self.filtered_particles,
                self.measurement_lines,
                self.current_result.settings,
                self.log_text.toPlainText(),
            )
            QMessageBox.information(self, "Export Complete", f"Results were exported to:\n{output_dir}")
            self.log(f"Results exported to: {output_dir}")
        except Exception as exc:
            traceback.print_exc()
            QMessageBox.critical(self, "Export Failed", str(exc))
            self.log(f"Export failed: {exc}")

    def _zoom_active_view(self, action: str) -> None:
        current_widget = self.tabs.currentWidget()
        if not isinstance(current_widget, ImageView):
            return
        if action == "in":
            current_widget.zoom_in()
        elif action == "out":
            current_widget.zoom_out()
        elif action == "reset":
            current_widget.reset_view()


    def _on_tab_changed(self, _index: int) -> None:
        current_widget = self.tabs.currentWidget()
        if isinstance(current_widget, ImageView) and current_widget.has_image():
            QTimer.singleShot(0, current_widget.reset_view)

    def closeEvent(self, event) -> None:
        if self.analysis_thread is not None and self.analysis_thread.isRunning():
            self.analysis_thread.quit()
            self.analysis_thread.wait(3000)
        if self.model_thread is not None and self.model_thread.isRunning():
            self.model_thread.quit()
            self.model_thread.wait(30000)
        if hasattr(self, "qt_log_handler"):
            self.logger.removeHandler(self.qt_log_handler)
        super().closeEvent(event)
