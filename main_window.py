"""
main_window.py

Contains the MainWindow class: the PyQt6 GUI for the OpenModelica
TwoConnectedTanks simulator app.

This module only handles presentation and user interaction. All simulation
logic lives in simulation_runner.py.
"""

from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from result_plotter import ResultParser, ResultPlotter
from simulation_runner import SimulationRunner


class MainWindow(QWidget):
    """Main application window for launching the TwoConnectedTanks simulation."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("TwoConnectedTanks Simulator")
        self.setMinimumWidth(480)

        self._runner: SimulationRunner | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout()

        form_layout = QGridLayout()

        # Executable picker
        form_layout.addWidget(QLabel("Executable:"), 0, 0)
        self.exe_path_field = QLineEdit()
        self.exe_path_field.setReadOnly(True)
        self.exe_path_field.setPlaceholderText("Select TwoConnectedTanks.exe...")
        form_layout.addWidget(self.exe_path_field, 0, 1)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._on_browse_clicked)
        form_layout.addWidget(browse_button, 0, 2)

        # Start time
        form_layout.addWidget(QLabel("Start time:"), 1, 0)
        self.start_time_spin = QSpinBox()
        self.start_time_spin.setRange(0, 100)
        self.start_time_spin.setValue(0)
        form_layout.addWidget(self.start_time_spin, 1, 1)

        # Stop time
        form_layout.addWidget(QLabel("Stop time:"), 2, 0)
        self.stop_time_spin = QSpinBox()
        self.stop_time_spin.setRange(0, 100)
        self.stop_time_spin.setValue(4)
        form_layout.addWidget(self.stop_time_spin, 2, 1)

        layout.addLayout(form_layout)

        # Run button
        self.run_button = QPushButton("Run Simulation")
        self.run_button.clicked.connect(self._on_run_clicked)
        layout.addWidget(self.run_button)

        # Status label
        self.status_label = QLabel("Status: Idle")
        layout.addWidget(self.status_label)

        # Output log
        layout.addWidget(QLabel("Output:"))
        self.output_log = QPlainTextEdit()
        self.output_log.setReadOnly(True)
        self.output_log.setMaximumHeight(120)
        layout.addWidget(self.output_log)

        # Result plot (populated after a successful run)
        layout.addWidget(QLabel("Tank Water Levels:"))
        self.plot_canvas: FigureCanvasQTAgg | None = None
        self.plot_placeholder = QLabel("Run a simulation to see results here.")
        self.plot_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plot_placeholder.setMinimumHeight(300)
        layout.addWidget(self.plot_placeholder)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _on_browse_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select simulation executable",
            "",
            "Executables (*.exe);;All Files (*)",
        )
        if file_path:
            self.exe_path_field.setText(file_path)

    def _on_run_clicked(self) -> None:
        exe_path = self.exe_path_field.text()
        start_time = self.start_time_spin.value()
        stop_time = self.stop_time_spin.value()

        self._runner = SimulationRunner(exe_path)

        self.run_button.setEnabled(False)
        self._set_status("Running...")
        self.output_log.clear()

        try:
            result = self._runner.run(start_time, stop_time)
        except (ValueError, FileNotFoundError) as exc:
            self._set_status("Error")
            QMessageBox.critical(self, "Invalid input", str(exc))
            self.run_button.setEnabled(True)
            return

        self.run_button.setEnabled(True)

        if result.success:
            self._set_status("Completed")
            self._show_result_plot(exe_path)
        else:
            self._set_status("Error")
            QMessageBox.warning(
                self,
                "Simulation failed",
                f"The executable exited with code {result.return_code}.",
            )

        self._append_output(result.stdout, result.stderr)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _set_status(self, text: str) -> None:
        self.status_label.setText(f"Status: {text}")

    def _append_output(self, stdout: str, stderr: str) -> None:
        if stdout:
            self.output_log.appendPlainText(stdout)
        if stderr:
            self.output_log.appendPlainText(stderr)

    def _show_result_plot(self, exe_path: str) -> None:
        """
        Locate the .mat result file next to the executable (OpenModelica
        names it '<ModelName>_res.mat') and plot the tank water levels.
        Silently does nothing if the result file or expected variables
        aren't found, so a missing plot never masks a successful run.
        """
        exe_dir = Path(exe_path).parent
        model_name = Path(exe_path).stem
        result_path = exe_dir / f"{model_name}_res.mat"

        if not result_path.is_file():
            return

        try:
            parser = ResultParser(str(result_path))
            plotter = ResultPlotter(parser)
            candidate_vars = [
                v for v in ("tank1.h", "tank2.h") if v in parser.available_variables()
            ]
            if not candidate_vars:
                return
            figure = plotter.plot_levels(candidate_vars)
        except (FileNotFoundError, ValueError, KeyError):
            return

        if self.plot_canvas is not None:
            self.layout().removeWidget(self.plot_canvas)
            self.plot_canvas.setParent(None)
        else:
            self.layout().removeWidget(self.plot_placeholder)
            self.plot_placeholder.setParent(None)

        self.plot_canvas = FigureCanvasQTAgg(figure)
        self.layout().addWidget(self.plot_canvas)
