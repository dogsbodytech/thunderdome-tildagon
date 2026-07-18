# Auto-discovered effect menu. Each .py in this folder is one menu item and
# must define: NAME (label shown), VALUE (string published over MQTT) and
# draw(ctx) (the dome graphic). Drop a new file in and it appears in the
# menu, sorted by filename — no registry to edit.
import os

_dir = __file__.rsplit("/", 1)[0] if "/" in __file__ else "."

# __import__ with a non-empty fromlist returns the leaf submodule itself.
EFFECTS = [
    __import__(__name__ + "." + _n, None, None, (_n,))
    for _n in sorted(
        f[:-3]
        for f in os.listdir(_dir)
        if f.endswith(".py") and f != "__init__.py"
    )
]
