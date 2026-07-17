# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

- `thunderdome-tildagon-app/` — Tildagon badge app (MicroPython) that publishes to MQTT. Symlinked into the simulator at `/Volumes/www/badge-2024-software/sim/apps/`.
- `dome-mqtt-broker/` — empty directory, presumably intended to hold an MQTT broker component.
- `Pipfile` — Pipenv config, Python 3.13.3, no packages declared yet.

## Tildagon badge reference

Docs: https://tildagon.badge.emfcamp.org/tildagon-apps/reference/reference/

Badge is an EMF Camp Tildagon (ESP32-S3, MicroPython). Desktop tooling (mypy, pytest) does not apply to on-badge code; test in the simulator at `/Volumes/www/badge-2024-software/sim/`. The sim's fake modules (`sim/fakes/`) are incomplete — e.g. `machine.unique_id()` is missing; guard badge-only APIs with `getattr` fallbacks.

### Buttons

Prefer `BUTTON_TYPES` — universal, works on both boards. `FRONTBOARD_BUTTON_TYPES` (A–F) and `JOYSTICK_BUTTON_TYPES` respond only to their own hardware.

Tildagon (2024): six buttons around the hexagonal perimeter, clockwise from top, screen facing you. Spaceagon (2026 frontboard, [docs](https://tildagon.badge.emfcamp.org/tildagon-apps/reference/spaceagon/)): same six buttons A–F in a row, plus 5-way joystick, 12-sensor touch strip, 2 proximity sensors.

| Input          | Type     | BUTTON_TYPES | Source-specific constant       | Tildagon position |
|----------------|----------|--------------|--------------------------------|-------------------|
| Button A       | button   | `UP`         | `FRONTBOARD_BUTTON_TYPES["A"]` | top               |
| Button B       | button   | `RIGHT`      | `FRONTBOARD_BUTTON_TYPES["B"]` | upper-right       |
| Button C       | button   | `CONFIRM`    | `FRONTBOARD_BUTTON_TYPES["C"]` | lower-right       |
| Button D       | button   | `DOWN`       | `FRONTBOARD_BUTTON_TYPES["D"]` | bottom            |
| Button E       | button   | `LEFT`       | `FRONTBOARD_BUTTON_TYPES["E"]` | lower-left        |
| Button F       | button   | `CANCEL`     | `FRONTBOARD_BUTTON_TYPES["F"]` | upper-left        |
| Joystick up    | joystick | `UP`         | `JOYSTICK_BUTTON_TYPES["UP"]`  | —                 |
| Joystick down  | joystick | `DOWN`       | `JOYSTICK_BUTTON_TYPES["DOWN"]`| —                 |
| Joystick left  | joystick | `LEFT`       | `JOYSTICK_BUTTON_TYPES["LEFT"]`| —                 |
| Joystick right | joystick | `RIGHT`      | `JOYSTICK_BUTTON_TYPES["RIGHT"]`| —                |
| Joystick press | joystick | `CONFIRM`    | `JOYSTICK_BUTTON_TYPES["SELECT"]` (fire) | —       |

Detect frontboard at runtime: `from frontboard.utils import detect_frontboard`. Specific source via `event.button.name` (e.g. `"FIRE"`).

```python
from events.input import Buttons, BUTTON_TYPES

self.button_states = Buttons(self)          # in __init__
if self.button_states.get(BUTTON_TYPES["CONFIRM"]):
    self.button_states.clear()              # clear or it re-triggers every update
```

Event-based alternative: `eventbus.on(ButtonDownEvent, handler, self.app)` — always `eventbus.remove(...)` on minimise/close.

### LEDs

12 LEDs, indexed 1–12:

```python
from tildagonos import tildagonos
tildagonos.set_led_power(True)
tildagonos.leds[1] = (255, 0, 0)
tildagonos.leds.write()
```

### MQTT

`mqtt.emf.camp` (1883 plain, 8883 TLS). 2026 policy: anonymous clients may subscribe to anything but publish only under `open/`. QoS 0 publishes to denied topics fail silently.

## Environment

- Python dependency management is via **Pipenv** (`Pipfile`, no `Pipfile.lock` yet).
  - Install deps: `pipenv install`
  - Add a package: `pipenv install <package>`
  - Run a command in the env: `pipenv run <command>`
  - Activate a shell: `pipenv shell`

There is no build, lint, or test tooling configured yet. Update this file once source code, dependencies, and tooling are added.
