import binascii
import json
import machine

import app
from umqtt.simple import MQTTClient, MQTTException
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
# logo at 12. Tapping a pad publishes the label's kebab-cased name
# (e.g. "kuiper-belt") as the effect name.
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
        self.retry_ms = 0
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

    def _connect_wifi(self):
        try:
            if wifi.status():
                return True
            wifi.disconnect()
            wifi.connect()
            return bool(wifi.wait())
        except OSError:
            return False

    def _connect_mqtt(self):
        try:
            # sim's fake machine module lacks unique_id; real badge has it
            unique = getattr(machine, "unique_id", lambda: b"sim")()
            client_id = b"dogsbody-" + binascii.hexlify(unique)
            self.client = MQTTClient(client_id, "mqtt.emf.camp")
            self.client.connect()
            return True
        except (OSError, MQTTException):
            self.client = None
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
            except (OSError, MQTTException):
                self.client = None
        return False

    # --- selection -------------------------------------------------------

    def _send_effect(self, value, label):
        # Payload is a JSON dict so params/brightness/colour can ride along later.
        payload = json.dumps({"name": value}).encode()
        ok = self._publish(TOPIC_BASE + b"/effect", payload)
        self.notification = Notification(
            'Sent "%s"' % label if ok else "Not connected"
        )

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
                self._send_effect(label.lower().replace(" ", "-"), label)

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

        if self.client is None:
            self.retry_ms -= delta
            if self.retry_ms <= 0:
                self.retry_ms = 5000
                # Never block the frame loop: wifi.connect()/wait() can stall
                # for seconds, so only pre-connect MQTT when WiFi is already
                # up. _publish() still does the full blocking connect on the
                # user-initiated path.
                try:
                    up = wifi.status()
                except OSError:
                    up = False
                if up:
                    self._connect_mqtt()

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
