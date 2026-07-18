# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

Publishable Tildagon app (see https://tildagon.badge.emfcamp.org/tildagon-apps/publish/). Runtime files live at the repo **root** — the app store requires `app.py` at the tarball's single root dir:

- `app.py` — the app (MicroPython); exports `__app_export__`. Effect-picker menu + touch passthrough + MQTT.
- `dome.py` — shared wireframe geometry (`DOME_SEGMENTS`, `DOME_TOP`/`DOME_BOTTOM`) + `draw_dome(ctx, color_fn)`.
- `effects/` — one module per menu item, auto-discovered (see **Adding an effect**).
- `tildagon.toml` — app-store metadata (name, category, author, license, url, description, version).
- `metadata.json` — local/sim launcher metadata; the app store regenerates this on install and strips `tildagon.toml`.
- `install-on-badge.py` — copies the whole tree (minus `__pycache__`/`.git`) to a connected badge via `mpremote`.

Symlinked into the simulator at `/Volumes/www/badge-2024-software/sim/apps/`. `.gitattributes` keeps dev/tooling files (`.claude`, `.agents`, `CLAUDE.md`, `Pipfile*`, `skills-lock.json`) out of the badge/app-store download via `export-ignore`.

### Adding an effect

The app is an effect picker: UP/DOWN scroll a built-in `Menu`, CONFIRM publishes `pressed` to `open/dogsbody/dome/<VALUE>` (same topic shape as the buttons/touch petals — `VALUE` is the topic leaf), that effect's dome preview draws as a backdrop, and one perimeter LED marks the scroll position. Touch petals (`TOUCH01–12`) publish `pressed` to `open/dogsbody/dome/TOUCHxx` directly, independent of the menu.

The effect `VALUE`s mirror the dome controller's effect files at `dogsbodytech/thunderdome` → `3d-controller/controller/thunderdome/effects/` (one badge module per non-procedural effect file, keyed by its stem: `clock_hand`, `expanding_rings`, `height_wave`). If the dome dispatches on hyphens instead, change each `VALUE` (one line).

Menu items are **auto-discovered** from `effects/` — one file per item, no registry to edit. To add one, drop `effects/<name>.py` defining `NAME`, `VALUE`, and `draw(ctx)`:

```python
from ..dome import draw_dome  # also DOME_TOP, DOME_BOTTOM for height gradients

NAME = "Height Wave"     # label shown in the menu
VALUE = "height_wave"    # topic leaf; CONFIRM publishes "pressed" there

def draw(ctx):     # the dome graphic; color_fn returns (r,g,b) 0–1 per segment
    band = (DOME_TOP + DOME_BOTTOM) / 2
    def color(x1, y1, x2, y2):
        my = (y1 + y2) / 2
        return (0.2, 1.0, 0.4) if abs(my - band) <= 14 else (0.0, 0.1, 0.05)
    draw_dome(ctx, color)
```

- `effects/__init__.py` imports every `.py` (except `__init__.py`), **sorted by filename** → that's the menu order. Never edit it to register a file.
- `draw_dome(ctx, color_fn)` strokes the wireframe; `color_fn(x1, y1, x2, y2)` is called per segment. Uniform colour = ignore the args and return a constant. Y grows **downward** (top ≈ `DOME_TOP` −67, bottom ≈ `DOME_BOTTOM` +54).
- No install step: `install-on-badge.py` copies the whole tree, so new effect files ship automatically.
- Empty `effects/` divides by zero (`% len(EFFECTS)`) — keep at least one file.

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
| Touch strip 1–12 | touch  | —            | `event.button.name == "TOUCH01"`…`"TOUCH12"` | —  |
| Proximity L/R  | proximity| —            | `event.button.name == "LEFTPROX"` / `"RIGHTPROX"` | — |

Touch and proximity (Spaceagon only) emit `ButtonDownEvent`/`ButtonUpEvent` but their `Button`s have no `BUTTON_TYPES` parent — invisible to `Buttons.get(BUTTON_TYPES[...])` polling and to `BUTTON_TYPES[...] in event.button`; match `event.button.name` instead.

Detect frontboard at runtime: `from frontboard.utils import detect_frontboard`. Specific source via `event.button.name` (e.g. `"FIRE"`).

```python
from events.input import Buttons, BUTTON_TYPES

self.button_states = Buttons(self)          # in __init__
if self.button_states.get(BUTTON_TYPES["CONFIRM"]):
    self.button_states.clear()              # clear or it re-triggers every update
```

Event-based alternative: `eventbus.on(ButtonDownEvent, handler, self)` — check which button with `BUTTON_TYPES["X"] in event.button`. Input events only reach the focused app (`InputEvent.requires_focus`), so handlers stay silent while minimised; the OS deregisters all handlers when an app closes. A handler that raises crashes the app.

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
