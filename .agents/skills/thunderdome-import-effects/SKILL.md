---
name: thunderdome-import-effects
description: Sync dome effects from the thunderdome controller repo into the badge effects/ folder. Use when asked to import, sync, add, or check for new dome effects, or after the controller's effect catalogue changes. Only adds effects that don't exist yet — never overwrites.
---

# Import dome effects

The badge app is an effect picker. Each file in `effects/` is one menu item,
auto-discovered by `effects/__init__.py`. The **source of truth** for which
effects exist is the dome controller repo:

- Repo: `dogsbodytech/thunderdome`
- Path: `3d-controller/controller/thunderdome/effects/`
- URL: https://github.com/dogsbodytech/thunderdome/tree/main/3d-controller/controller/thunderdome/effects

This skill finds effects in that folder that are **not yet** in the local
`effects/` folder and creates a badge module for each.

## Selection rule

An effect is any `.py` file in the controller effects folder **whose name does
NOT start with `_`**. Everything else is infrastructure — ignore it.

```sh
gh api "repos/dogsbodytech/thunderdome/contents/3d-controller/controller/thunderdome/effects?ref=main" \
  --jq '.[] | select(.type=="file") | .name | select(startswith("_") | not) | select(endswith(".py"))'
```

> Safeguard: at time of writing, `Registry.py`, `Common.py`, and `Procedural.py`
> are shared infrastructure that do **not** start with `_`, so the rule above
> would wrongly include them. Skip any candidate that is not an actual renderer
> (open it — a real effect defines a `render_*` / effect function, not a
> catalogue/dataclass/helper). If a candidate is ambiguous, ask the human
> rather than importing it. Procedural effects (defined only inside
> `Procedural.py` / the registry, with no file of their own) are out of scope.

## Steps

1. **List remote effects** with the command above → set of stems (drop `.py`).
2. **List local effects**: `ls effects/*.py` minus `__init__.py` → local stems.
3. **Diff**: remote − local = the effects to create. If empty, report "nothing
   to import" and stop.
4. **For each missing effect**:
   a. Read its source from the controller repo to understand what it does:
      ```sh
      gh api "repos/dogsbodytech/thunderdome/contents/3d-controller/controller/thunderdome/effects/<stem>.py?ref=main" \
        --jq '.content' | base64 -d
      ```
   b. Create `effects/<stem>.py` (see template + preview guidance below).
   c. **Never overwrite an existing `effects/<stem>.py`.** Only create files
      that are absent. If a stem already exists, skip it — do not modify it.
5. **Verify** (see below), then report what was added.

No registry edit is ever needed — `effects/__init__.py` auto-discovers files,
sorted by filename, and `install-on-badge.py` copies the whole tree.

## Effect module contract

Each `effects/<stem>.py` must define exactly:

- `NAME` — menu label. Stems are PascalCase; derive by inserting a space
  before each interior capital (`ClockHand` → "Clock Hand") unless the source
  suggests a better human name.
- `VALUE` — the effect name. Use the **file stem verbatim** (e.g.
  `ClockHand`). CONFIRM publishes it as the **payload** to
  `open/dogsbody/thunderdome/effect`, and the dome's MQTT bridge only accepts
  names matching `[A-Z][A-Za-z0-9]{0,63}`. (If the dome's naming convention
  changes again, change `VALUE` only — one line.)
- `draw(ctx)` — a static 2D preview of the effect, drawn as the menu backdrop.

### Preview guidance

Previews use the shared helper in `dome.py`:

```python
from ..dome import draw_dome                    # + DOME_TOP, DOME_BOTTOM if needed
draw_dome(ctx, color_fn)   # color_fn(x1, y1, x2, y2) -> (r, g, b) floats 0.0-1.0
```

`draw_dome` strokes the wireframe once per segment, calling `color_fn` for each.
Screen origin is centre `(0, 0)`; **y grows downward**; dome spans y ≈
`DOME_TOP` (−67, top) to `DOME_BOTTOM` (+54, bottom). Pick a `color_fn` that
matches the effect's geometry — highlight the relevant struts, dim the rest:

| Effect shape (from source) | Preview approach | Example in repo |
|---|---|---|
| Radial / angular sweep (a "hand", radar) | `math.atan2(my, mx)`; bright wedge near a fixed angle | `effects/ClockHand.py` |
| Expanding shells / distance from centre | `math.sqrt(mx**2+my**2)`; alternate bright/dim bands | `effects/ExpandingRings.py` |
| Height / Z band moving vertically | bright band where `abs(my - band_y) <= h` | `effects/HeightWave.py` |
| Gradient / palette fill (fire, aurora) | interpolate colour by height using `DOME_TOP`/`DOME_BOTTOM` | — |

(`mx, my` = segment midpoint `(x1+x2)/2, (y1+y2)/2`.) Keep the preview readable
against the menu text drawn on top: one clear highlight colour, a dim/dark
background colour. Import `math` in the module if you use trig.

### Template

```python
import math

from ..dome import draw_dome

NAME = "Clock Hand"
VALUE = "ClockHand"

_ANGLE = math.radians(-60)
_HALF = math.radians(24)
_TAU = 2 * math.pi


def draw(ctx):
    def color(x1, y1, x2, y2):
        a = math.atan2((y1 + y2) / 2, (x1 + x2) / 2)
        d = abs(((a - _ANGLE + math.pi) % _TAU) - math.pi)
        return (1.0, 1.0, 1.0) if d <= _HALF else (0.14, 0.14, 0.2)

    draw_dome(ctx, color)
```

Use `2 * math.pi`, not `math.tau` (not on the badge). No mutable module-level
state; `draw` must be pure given `ctx`.

## Verify

The badge simulator's `ctx`/`wasmtime` layer is currently broken, so a full
render/screenshot may not run. Verify the logic instead: discovery loads every
new file and each exposes `NAME`, `VALUE`, `draw`.

```sh
python3 - <<'PY'
import sys, types, importlib
sys.path.insert(0, "effects")          # so `dome` resolves for the bare import
# minimal check: import each new module directly and confirm the contract
import os
for f in sorted(os.listdir("effects")):
    if f.endswith(".py") and not f.startswith("_"):
        src = open(os.path.join("effects", f)).read()
        assert "NAME" in src and "VALUE" in src and "def draw(" in src, f
        print("ok", f)
PY
```

For a fuller check (auto-discovery + colouring + publish wiring) adapt the
harness pattern: stub the badge modules (`app`, `app_components`, `tildagonos`,
`wifi`, `umqtt.simple`, `machine`, `events.input`, `system.eventbus`), add
`badge-2024-software/sim/apps` to `sys.path`, import the package
`thunderdome-tildagon-app`, then assert `app.EFFECTS` contains the new names and
each `draw(ctx)` records segments against a recording fake `ctx`.

## Guardrails

- **Never overwrite** an existing `effects/*.py` — this skill only adds.
- **Never replace an existing skill file.** If `.ai/skills/import-effects.md`
  already exists, do not clobber it.
- Skip `_`-prefixed files and non-renderer infrastructure modules.
- One file per effect; do not edit `effects/__init__.py`.
