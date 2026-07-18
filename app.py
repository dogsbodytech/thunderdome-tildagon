import binascii
import machine

import app
from umqtt.simple import MQTTClient, MQTTException
import wifi

from app_components import Menu, Notification, clear_background
from events.input import ButtonDownEvent
from system.eventbus import eventbus
from tildagonos import tildagonos

from .effects import EFFECTS

# mqtt.emf.camp only allows anonymous publish under open/ (2026 policy)
TOPIC_BASE = b"open/dogsbody/dome"


class ThunderdomeApp(app.App):
    def __init__(self):
        self.client = None
        self.retry_ms = 0
        self.notification = None
        self._led_pos = -1  # forces the LED ring to draw on the first update
        # Menu owns UP/DOWN scroll, CONFIRM -> select, CANCEL -> back. Its
        # button handler requires focus, so it goes quiet while minimised.
        self.menu = Menu(
            self,
            [e.NAME for e in EFFECTS],
            select_handler=self._select,
            back_handler=self.minimise,
        )
        # Touch petals have no BUTTON_TYPES parent, so the Menu never sees
        # them — this handler passes TOUCH01-12 straight through to MQTT.
        # Input events require focus, so it stays quiet while minimised.
        eventbus.on(ButtonDownEvent, self._on_button_down, self)
        tildagonos.set_led_power(True)

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

    def _select(self, item, idx):
        # Same topic shape as the buttons/touch petals: the effect's VALUE is
        # the topic leaf, published "pressed".
        effect = EFFECTS[idx % len(EFFECTS)]
        ok = self._publish(TOPIC_BASE + b"/" + effect.VALUE.encode(), b"pressed")
        self.notification = Notification(
            'Sent "%s"' % effect.NAME if ok else "Not connected"
        )

    def _on_button_down(self, event):
        # Touch petals only; d-pad/confirm/cancel belong to the Menu.
        name = event.button.name
        if name and name.startswith("TOUCH"):
            ok = self._publish(TOPIC_BASE + b"/" + name.encode(), b"pressed")
            self.notification = Notification(name if ok else "Not connected")

    def _update_leds(self, idx):
        # One lit perimeter LED marks the scroll position (indices 1-12).
        for i in range(1, 13):
            tildagonos.leds[i] = (0, 0, 0)
        tildagonos.leds[1 + idx % 12] = (255, 255, 255)
        tildagonos.leds.write()

    def update(self, delta):
        idx = self.menu.position % len(EFFECTS)
        if idx != self._led_pos:
            self._led_pos = idx
            self._update_leds(idx)

        self.menu.update(delta)
        if self.notification:
            self.notification.update(delta)

        if self.client is None:
            self.retry_ms -= delta
            if self.retry_ms <= 0:
                self.retry_ms = 5000
                if self._connect_wifi():
                    self._connect_mqtt()

    def draw(self, ctx):
        clear_background(ctx)
        # Focused effect's dome preview, drawn as a backdrop behind the menu.
        ctx.save()
        EFFECTS[self.menu.position % len(EFFECTS)].draw(ctx)
        ctx.restore()
        self.menu.draw(ctx)
        if self.notification:
            self.notification.draw(ctx)


__app_export__ = ThunderdomeApp
