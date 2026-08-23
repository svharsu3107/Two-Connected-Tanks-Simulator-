# TwoConnectedTanks Simulator

**A Python + PyQt6 desktop app that puts a friendly face on an OpenModelica simulation — and actually shows you the water flow, not just a "success" message.**

![Python](https://img.shields.io/badge/Python-3.6+-blue?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41cd52?logo=qt&logoColor=white)
![OpenModelica](https://img.shields.io/badge/Simulation-OpenModelica-orange)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?logo=windows)




## 📖 Table of Contents

- [What this actually does](#-what-this-actually-does)
- [The physics behind it](#-the-physics-behind-it)
- [See it in action](#-see-it-in-action)
- [Architecture](#-architecture--why-4-files-not-1)
- [Getting started](#-getting-started)
- [Rebuilding the model yourself](#-rebuilding-the-model-yourself-optional)
- [The debugging story](#-the-debugging-story-tank2mo)
- [Constraints](#-constraints)

---

## 🧠 What this actually does

Most solutions to this task are, structurally, the same handful of
widgets wired to `subprocess.run()`. This one is too, underneath — but
it's built so that **every piece has exactly one job**, inputs are
validated *before* anything runs, failures explain themselves instead of
crashing silently, and — the part most versions skip — **you can
actually see the simulation result** as a live chart inside the app,
not just a pass/fail message.

The workflow:

1. **Browse** to the compiled `TwoConnectedTanks` executable.
2. Enter a **start time** and **stop time** — integers satisfying
   `0 ≤ start < stop < 5`.
3. Click **Run Simulation**.
4. Watch the status go `Idle → Running… → Completed`, read the real
   simulation log, and see a plot of both tanks' water levels appear.

---

## 🌊 The physics behind it

`TwoConnectedTanks` couples two tanks through a connector (`FlowConnect`):

| | Tank 1 | Tank 2 |
|---|---|---|
| Inflow | Constant `Qin = 2` | Whatever leaves Tank 1 |
| Outflow | `0` until `t = 5s`, then `√h` | Governed by connector flow `Q1` |
| Behaviour | Fills steadily | Starts responding once flow arrives |

Because Tank 1's outflow is deliberately held at `0` for the first five
seconds, the connector flow into Tank 2 is also `0` for that entire
window — which is exactly what broke the model originally (see
[the debugging story](#-the-debugging-story-tank2mo) below).

---

## 🖥️ See it in action

![TwoConnectedTanks Simulator — a completed run showing the tank water level plot](docs/screenshot.png)

*A completed run: `startTime=0`, `stopTime=4` — Tank 1 fills steadily
while Tank 2 stays flat, since no flow reaches it before the connector
activates.*

---

## 🏗️ Architecture — why 4 files, not 1 ?

| File | Responsibility | Depends on |
|---|---|---|
| `main.py` | Launches the app | `main_window` |
| `main_window.py` | GUI — collects input, shows results | `simulation_runner`, `result_plotter` |
| `simulation_runner.py` | Validates input, builds the command, runs the executable | *nothing GUI-related* |
| `result_plotter.py` | Parses the `.mat` result file, builds a chart | *nothing GUI-related* |

The point of this split: `SimulationRunner` and `ResultParser` /
`ResultPlotter` have **zero knowledge of PyQt**. You could swap the
entire GUI for a command-line tool tomorrow and none of the simulation
or parsing logic would need to change. Each class is independently
testable — which is exactly how the input-validation logic and the
`.mat`-parsing logic were verified, before ever touching a real GUI.

---

## 🚀 Getting started...

**Requirements:** Windows 10/11, Python 3.6+

```bash
git clone <this-repo-url>
cd <repo-folder>
pip install -r requirements.txt
python main.py
```

Then, in the app:
1. Click **Browse…**, select `TwoConnectedTanks.exe` (already included in this repo).
2. Set **Start time** / **Stop time** — must satisfy `0 ≤ start < stop < 5`.
3. Click **Run Simulation** and watch the result appear.

---

## 🔧 Rebuilding the model yourself

The compiled executable and its runtime dependencies are already in
this repo, but if you want to regenerate it from the Modelica source:

1. Install [OpenModelica](https://openmodelica.org/) and open **OMEdit**.
2. **File → Open Model/Library File(s)** → select `package.mo` (this
   loads `Tank`, `Tank2`, `FlowConnect`, and `TwoConnectedTanks` together).
3. Select `TwoConnectedTanks` → **Simulation → Simulate**.
4. The new executable and its dependencies land in OMEdit's working
   directory (**Tools → Options → General → Working Directory**).

---

## 🐛 The debugging story (Tank2.mo)

This is the part that took the longest — and the part worth being able
to explain, because it's real engineering, not boilerplate.

The original model had:

```modelica
T = V / Q1;
```

Tank 1's outflow is forced to `0` for the first 5 seconds
(`if time <= 5.0 then Qo = 0.0`), which means the connector flow into
Tank 2 — `Q1` — is also `0` for that entire window. Every simulation
attempt failed instantly with a **division-by-zero** error at `t = 0`.

**The fix:**

```modelica
T = V / (Q1 + 1e-8);
```

A tiny epsilon prevents the crash without meaningfully changing the
physics — `1e-8` is negligible next to any real flow value. This was
verified directly against the compiled executable's own output: the
real result file shows `tank2.T = 1x10^9` exactly (`10 / 1e-8`),
confirming the fix is live in the actual binary, not just the source.

A second, unrelated gotcha along the way: OpenModelica's generic
`-override=startTime=...,stopTime=...` flag **does not work** for
simulation timing — it logs a warning ("override variable name not
found in model") and silently keeps the default duration. The fix was
switching to the dedicated `-startTime` / `-stopTime` flags, which the
executable actually respects.

---

## 📋 Constraints

- `0 ≤ start_time < stop_time < 5` — enforced in `SimulationRunner`,
  with a clear `QMessageBox` if violated.
- The included `.exe` and `.dll` files are Windows binaries; running on
  Linux requires rebuilding the model with a Linux OpenModelica install.

---

## 💧 Closing thought

Two tanks, one pipe, and a lot more debugging than the spec sheet lets
on. Somewhere between a division-by-zero at `t = 0` and a silently
ignored command-line flag, this stopped being "just a wrapper around
`subprocess.run()`" and became an actual small piece of software —
one with a bug history, a design rationale, and a UI that tells you the
truth about what it's doing.

If Tank 1 can patiently fill up for four seconds waiting on Tank 2 to
catch up, this README can wait for you to finish reading it too.

**Thanks for reading this far — now go run the simulation.** 🌊


