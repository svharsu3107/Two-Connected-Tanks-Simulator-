"""
result_plotter.py

Contains the ResultParser and ResultPlotter classes, responsible for reading
an OpenModelica simulation result (.mat) file and rendering the tank water
levels over time.

OpenModelica writes results in a MATLAB v4/v5 file containing (at minimum):
    - 'name'   : a char matrix where each COLUMN is one variable's name,
                 padded with spaces to a common length.
    - 'data_2' : a matrix of shape (n_variables, n_timesteps) holding the
                 time-varying trajectory of each variable, in the same
                 order as the columns of 'name'. Row 0 is always 'time'.

This module has no knowledge of PyQt - ResultParser can be tested with
plain Python, and ResultPlotter only depends on matplotlib.
"""

from pathlib import Path

import numpy as np
from scipy.io import loadmat


class ResultParser:
    """
    Reads variable trajectories out of an OpenModelica .mat result file.

    OpenModelica result files (v1.1) contain:
        - 'name'     : an array of strings; reading character j across all
                       rows and joining gives the name of variable j.
        - 'dataInfo' : a (4, n_vars) int array. For each variable column j:
                           dataInfo[0][j] -> which data matrix (1 or 2)
                           dataInfo[1][j] -> 1-based row index in that matrix
                       Matrix 1 ('data_1') holds constants/parameters (one
                       value repeated). Matrix 2 ('data_2') holds the actual
                       time-varying trajectories, with row 0 always 'time'.
        - 'data_1', 'data_2' : the two data matrices described above.
    """

    def __init__(self, mat_path: str) -> None:
        self.mat_path = Path(mat_path)
        if not self.mat_path.is_file():
            raise FileNotFoundError(f"Result file not found: {mat_path}")

        self._raw = loadmat(str(self.mat_path))

        required = ("name", "dataInfo", "data_2")
        missing = [key for key in required if key not in self._raw]
        if missing:
            raise ValueError(
                f"Missing expected key(s) {missing} in .mat file - "
                "unexpected OpenModelica result format."
            )

        self._names = self._extract_names()
        self._data_info = self._raw["dataInfo"]
        self._data_1 = self._raw.get("data_1")
        self._data_2 = self._raw["data_2"]

    def _extract_names(self) -> list[str]:
        """
        Decode OpenModelica's transposed 'name' representation: each
        character position j across all rows of 'name' spells out variable
        name j when joined and stripped of null/space padding.
        """
        name_rows = self._raw["name"]
        n_vars = len(name_rows[0]) if len(name_rows) > 0 else 0

        names = []
        for j in range(n_vars):
            chars = [
                row[j] if j < len(row) else "" for row in name_rows
            ]
            name = "".join(chars).rstrip("\x00").strip()
            names.append(name)
        return names

    def available_variables(self) -> list[str]:
        """Return all variable names found in the result file (excluding time)."""
        return [n for n in self._names if n != "time"]

    def get_series(self, variable_name: str) -> tuple[np.ndarray, np.ndarray]:
        """
        Return (time, values) arrays for the given variable name.

        Constant/parameter variables (stored in data_1) are expanded into
        a flat line spanning the full simulated time range.

        Raises:
            KeyError: if the variable name isn't present in the result file.
        """
        if "time" not in self._names:
            raise KeyError("'time' variable missing from result file.")

        time_col = self._names.index("time")
        time = np.asarray(self._data_2[abs(self._data_info[1][time_col]) - 1]).flatten()

        if variable_name not in self._names:
            raise KeyError(
                f"Variable '{variable_name}' not found. "
                f"Available: {self.available_variables()}"
            )

        var_col = self._names.index(variable_name)
        matrix_id = self._data_info[0][var_col]
        row_index = abs(self._data_info[1][var_col]) - 1

        if matrix_id == 2:
            values = np.asarray(self._data_2[row_index]).flatten()
        elif matrix_id == 1 and self._data_1 is not None:
            constant_value = self._data_1[row_index][0]
            values = np.full_like(time, constant_value, dtype=float)
        else:
            raise KeyError(
                f"Unrecognised data matrix id {matrix_id} for '{variable_name}'."
            )

        return time, values


class ResultPlotter:
    """
    Builds a matplotlib Figure showing one or more variable trajectories
    from a parsed simulation result.
    """

    def __init__(self, parser: ResultParser) -> None:
        self.parser = parser

    def plot_levels(self, variable_names: list[str]):
        """
        Create and return a matplotlib Figure plotting each requested
        variable against time on the same axes.
        """
        import matplotlib.figure

        figure = matplotlib.figure.Figure(figsize=(5, 3.5), dpi=100)
        axes = figure.add_subplot(111)

        for name in variable_names:
            try:
                time, values = self.parser.get_series(name)
            except KeyError:
                continue
            axes.plot(time, values, label=name)

        axes.set_xlabel("time (s)")
        axes.set_ylabel("water level (h)")
        axes.set_title("Tank Water Levels")
        axes.legend()
        axes.grid(True, linestyle="--", alpha=0.5)
        figure.tight_layout()
        return figure
