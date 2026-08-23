"""
simulation_runner.py

Contains the SimulationRunner class, which is responsible for building the
correct command-line arguments for an OpenModelica-generated executable and
running it as a subprocess.

This module has no knowledge of any GUI code - it can be tested and reused
independently of PyQt6.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SimulationResult:
    """Holds the outcome of a single simulation run."""

    success: bool
    return_code: int
    stdout: str
    stderr: str


class SimulationRunner:
    """
    Wraps execution of an OpenModelica simulation executable.

    Responsible for:
        - Validating the executable path and start/stop times.
        - Building the correct '-override' command-line flags.
        - Running the executable via subprocess and capturing output.
    """

    #: Task constraint: 0 <= start_time < stop_time < MAX_STOP_TIME
    MAX_STOP_TIME = 5

    def __init__(self, executable_path: str) -> None:
        self.executable_path = executable_path

    def validate_inputs(self, start_time: int, stop_time: int) -> None:
        """
        Validate start/stop time against the task's required condition:
        0 <= start_time < stop_time < 5

        Raises:
            ValueError: if any constraint is violated.
            FileNotFoundError: if the executable path is missing/invalid.
        """
        if not self.executable_path:
            raise FileNotFoundError("No executable selected.")

        exe_path = Path(self.executable_path)
        if not exe_path.is_file():
            raise FileNotFoundError(
                f"Executable not found: {self.executable_path}"
            )

        if start_time < 0:
            raise ValueError("Start time must be >= 0.")

        if start_time >= stop_time:
            raise ValueError("Start time must be less than stop time.")

        if stop_time >= self.MAX_STOP_TIME:
            raise ValueError(
                f"Stop time must be less than {self.MAX_STOP_TIME}."
            )

    def build_command(self, start_time: int, stop_time: int) -> list[str]:
        """
        Build the command-line argument list for the executable.

        OpenModelica executables expose simulation timing through the
        dedicated '-startTime' and '-stopTime' flags. The generic
        '-override=startTime=...,stopTime=...' form does NOT work here:
        the executable logs "override variable name not found in model"
        and silently keeps its default simulation duration, since
        startTime/stopTime are simulation settings, not model variables.

        Reference:
        https://openmodelica.org/doc/OpenModelicaUsersGuide/latest/simulationflags.html#simflagoverride
        """
        return [
            self.executable_path,
            f"-startTime={start_time}",
            f"-stopTime={stop_time}",
        ]

    def run(self, start_time: int, stop_time: int) -> SimulationResult:
        """
        Validate inputs, build the command, and execute the simulation.

        Returns:
            SimulationResult with success flag, return code, stdout, stderr.

        Raises:
            ValueError / FileNotFoundError: propagated from validate_inputs.
        """
        self.validate_inputs(start_time, stop_time)
        command = self.build_command(start_time, stop_time)

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(Path(self.executable_path).parent),
            )
        except subprocess.TimeoutExpired as exc:
            return SimulationResult(
                success=False,
                return_code=-1,
                stdout=exc.stdout or "",
                stderr="Simulation timed out after 60 seconds.",
            )
        except OSError as exc:
            return SimulationResult(
                success=False,
                return_code=-1,
                stdout="",
                stderr=f"Failed to launch executable: {exc}",
            )

        return SimulationResult(
            success=completed.returncode == 0,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
