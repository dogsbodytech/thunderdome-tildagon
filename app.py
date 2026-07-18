import asyncio
import binascii
import json
import machine

import app
from async_helpers import unblock
from umqtt.simple import MQTTClient
import wifi

from app_components import Menu, Notification, clear_background
from events.input import ButtonDownEvent, BUTTON_TYPES
from system.eventbus import eventbus
from tildagonos import tildagonos

from .effects import EFFECTS

# mqtt.emf.camp only allows anonymous publish under open/ (2026 policy)
TOPIC_BASE = b"open/dogsbody/thunderdome"

# Spaceagon touch pads TOUCH01-TOUCH12 run clockwise starting just right of
# 12 o'clock (angle = i/12*2pi - 0.42pi, per emfcamp's spaceagon-test app).
# The 2026 frontboard art prints one solar-system feature on each pad —
# planets, but also Sol, two belts and Voyager 1 — clockwise from the EMF
# logo at 12. Tapping a pad publishes the label's TitleCased name
# (e.g. "KuiperBelt") as the effect name — the dome's MQTT bridge only
# accepts names matching [A-Z][A-Za-z0-9]*.
# ponytail: pad-to-body mapping read from an artwork photo — rotate this
# list if a real badge shows otherwise.
SPACE_BODIES = [
    "Asteroid Belt",  # TOUCH01, ~12:30
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Kuiper Belt",
    "Voyager 1",
    "Sol",
    "Mercury",
    "Venus",
    "Earth",
    "Mars",  # TOUCH12, ~11:30
]


class ThunderdomeApp(app.App):
    def __init__(self):
        self.client = None
        self._outbox = []  # queued (topic, payload, label) for background_task
        self.notification = None
        self._led_pos = -1  # forces the LED ring to draw on the first update
        self.menu = None
        self.mode = "top"
        self._open_top()
        # Touch pads have no BUTTON_TYPES parent, so the Menu component never
        # sees them; catch them (and CANCEL, when no menu exists) ourselves.
        # Requires focus, so it goes quiet while minimised.
        eventbus.on(ButtonDownEvent, self._on_button_down, self)
        tildagonos.set_led_power(True)

    # --- modes -----------------------------------------------------------

    def _swap_menu(self, menu):
        if self.menu is not None:
            self.menu._cleanup()
        self.menu = menu
        self._led_pos = -1

    def _open_top(self):
        self.mode = "top"
        self._swap_menu(
            Menu(
                self,
                ["Effects", "Spaceagon"],
                select_handler=self._top_select,
                back_handler=self.minimise,
            )
        )

    def _top_select(self, item, idx):
        if item == "Effects":
            self._open_effects()
        else:
            self._open_spaceagon()

    def _open_effects(self):
        self.mode = "effects"
        self._swap_menu(
            Menu(
                self,
                [e.NAME for e in EFFECTS],
                select_handler=self._select_effect,
                back_handler=self._open_top,
            )
        )

    def _open_spaceagon(self):
        self.mode = "spaceagon"
        self._swap_menu(None)

    # --- connectivity ----------------------------------------------------
    # Everything here blocks on sockets: wifi.wait() spins for up to ~20s
    # and umqtt's connect()/publish() have no timeout. The badge runs
    # rendering, input and every app on one asyncio loop, so these must only
    # run on the worker thread background_task() spawns via unblock() —
    # never directly on the loop.

    def _connect_wifi(self):
        try:
            if wifi.status():
                return True
            wifi.disconnect()
            wifi.connect()
            return bool(wifi.wait())
        except Exception:
            return False

    def _drop_client(self):
        client, self.client = self.client, None
        if client is None:
            return
        try:
            client.disconnect()  # the only umqtt call that closes the socket
        except Exception:
            try:
                client.sock.close()
            except Exception:
                pass

    def _connect_mqtt(self):
        try:
            # sim's fake machine module lacks unique_id; real badge has it
            unique = getattr(machine, "unique_id", lambda: b"sim")()
            client_id = b"dogsbody-" + binascii.hexlify(unique)
            self.client = MQTTClient(client_id, "mqtt.emf.camp")
            self.client.connect()
            # Bound how long a dead broker can stall the worker thread.
            settimeout = getattr(self.client.sock, "settimeout", None)
            if settimeout:
                settimeout(10)
            return True
        except Exception:
            # umqtt raises more than OSError on a malformed CONNACK
            # (IndexError, AssertionError, ...) — catch everything.
            self._drop_client()
            return False

    def _publish(self, topic, payload):
        # ponytail: QoS 0 — one reconnect+retry covers a dropped idle
        # connection; a publish can still be silently lost beyond that.
        for _ in range(2):
            if self.client is None:
                if not (self._connect_wifi() and self._connect_mqtt()):
                    return False
            try:
                self.client.publish(topic, payload)
                return True
            except Exception:
                self._drop_client()
        return False

    # --- selection -------------------------------------------------------

    def _send_effect(self, value, label):
        # Payload is a JSON dict so params/brightness/colour can ride along later.
        payload = json.dumps({"name": value}).encode()
        self._outbox.append((TOPIC_BASE + b"/effect", payload, label))
        # Immediate feedback; background_task replaces this with the result.
        self.notification = Notification("Sending...")

    def _select_effect(self, item, idx):
        effect = EFFECTS[idx % len(EFFECTS)]
        self._send_effect(effect.VALUE, effect.NAME)

    def _on_button_down(self, event):
        if self.mode != "spaceagon":
            return
        if BUTTON_TYPES["CANCEL"] in event.button:
            self._open_top()
            return
        name = getattr(event.button, "name", "")
        if name.startswith("TOUCH"):
            try:
                idx = int(name[5:]) - 1
            except ValueError:
                return
            if 0 <= idx < len(SPACE_BODIES):
                label = SPACE_BODIES[idx]
                self._send_effect(label.replace(" ", ""), label)

    # --- LEDs ------------------------------------------------------------

    def _update_leds(self):
        # One lit perimeter LED marks the menu scroll position (indices
        # 1-12); no menu (spaceagon mode) leaves the ring dark.
        for i in range(1, 13):
            tildagonos.leds[i] = (0, 0, 0)
        if self.menu is not None:
            tildagonos.leds[1 + self._led_pos % 12] = (255, 255, 255)
        tildagonos.leds.write()

    # --- app loop --------------------------------------------------------

    def update(self, delta):
        if self.menu is not None:
            idx = self.menu.position % len(self.menu.menu_items)
            if idx != self._led_pos:
                self._led_pos = idx
                self._update_leds()
            self.menu.update(delta)
        elif self._led_pos == -1:
            self._led_pos = -2  # sentinel: ring darkened once
            self._update_leds()

        if self.notification:
            self.notification.update(delta)

    async def background_task(self):
        # All network I/O lives here, handed to a real _thread by unblock()
        # so the shared asyncio loop never stalls. One await at a time, so
        # only one worker thread ever touches self.client.
        async def idle():
            pass

        retry_ms = 0
        while True:
            if self._outbox:
                topic, payload, label = self._outbox.pop(0)
                ok = await unblock(self._publish, idle, topic, payload)
                self.notification = Notification(
                    'Sent "%s"' % label if ok else "Not connected"
                )
            elif self.client is None:
                retry_ms -= 50
                if retry_ms <= 0:
                    retry_ms = 5000
                    # Pre-connect when WiFi is already up so the first
                    # CONFIRM doesn't pay the MQTT connect cost.
                    try:
                        up = wifi.status()
                    except Exception:
                        up = False
                    if up:
                        await unblock(self._connect_mqtt, idle)
            await asyncio.sleep(0.05)

    def _draw_spaceagon(self, ctx):
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.rgb(1, 1, 1).move_to(0, 0).text("Tap the Planet!")
        ctx.restore()

    def draw(self, ctx):
        clear_background(ctx)
        if self.mode == "effects":
            # Focused effect's dome preview, drawn as a backdrop behind the menu.
            ctx.save()
            EFFECTS[self.menu.position % len(EFFECTS)].draw(ctx)
            ctx.restore()
        elif self.mode == "spaceagon":
            self._draw_spaceagon(ctx)
        if self.menu is not None:
            self.menu.draw(ctx)
        if self.notification:
            self.notification.draw(ctx)


__app_export__ = ThunderdomeApp
