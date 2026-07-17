import binascii
import machine

import app
from umqtt.simple import MQTTClient, MQTTException
import wifi

from app_components.tokens import line_height
from events.input import Buttons, BUTTON_TYPES

# mqtt.emf.camp only allows anonymous publish under open/ (2026 policy)
TOPIC_BASE = b"open/dogsbody/dome"

# BUTTON_TYPES is universal: Spaceagon joystick maps into the same names
BUTTON_NAMES = ["UP", "RIGHT", "CONFIRM", "DOWN", "LEFT", "CANCEL"]

IDLE_AFTER_MS = 3000

# 2V geodesic hemisphere wireframe, precomputed from dome/Assembly.drawio.svg
# geometry (2V = 2 strut classes, so red/blue only; source 3V had a third).
# Coordinates are screen-space, centred on (0, 0), for the 240x240 display.
DOME_SEGMENTS = (
    ((1.0, 0.2, 0.2), (
        (-25, -46, 26, -40), (-69, -31, -40, -61), (15, -37, 26, 10),
        (26, -40, 65, -37), (26, -40, 56, 1), (-40, -43, 0, -65),
        (-69, 0, -40, -43), (-81, -23, -69, -31), (0, -4, 26, -40),
        (-69, -31, -25, -46), (26, 10, 56, 49), (50, -52, 85, -15),
        (0, -65, 15, -37), (-90, 16, -69, -31), (-90, 34, -69, 0),
        (-81, -23, -69, 0), (-25, 1, 26, 10), (65, -8, 85, -15),
        (0, -65, 15, -67), (26, 10, 65, -8), (65, -37, 85, -15),
        (85, -15, 90, 16), (15, -67, 26, -40), (0, 54, 26, 10),
        (0, -65, 50, -52), (-69, -31, -56, 1), (-69, 0, -25, 1),
        (85, -15, 90, 34), (-69, 0, -56, 49), (-40, -61, 0, -65),
    )),
    ((0.25, 0.4, 1.0), (
        (-25, -46, 0, -4), (50, -52, 65, -8), (-90, 34, -56, 49),
        (-25, 1, 0, 54), (-56, 1, 0, -4), (-90, 34, -81, -23),
        (-40, -43, -25, 1), (-25, 1, 15, -37), (-56, 1, -25, -46),
        (15, -37, 50, -52), (15, -37, 65, -8), (56, 49, 65, -8),
        (15, -67, 50, -52), (-40, -43, 15, -37), (0, -4, 56, 1),
        (-90, 16, -81, -23), (50, -52, 65, -37), (-40, -61, 15, -67),
        (0, 54, 56, 49), (-81, -23, -40, -43), (-25, -46, 15, -67),
        (90, 34, 90, 16), (-90, 16, -56, 1), (56, 1, 90, 16),
        (-90, 34, -90, 16), (65, -37, 90, 16), (56, 1, 65, -37),
        (15, -67, 65, -37), (-40, -61, -25, -46), (56, 49, 90, 34),
        (-56, 49, -25, 1), (-56, 49, 0, 54), (65, -8, 90, 34),
        (-40, -43, -40, -61), (-81, -23, -40, -61),
    )),
)

class ThunderdomeApp(app.App):
    def __init__(self):
        self.button_states = Buttons(self)
        self.message = "Starting..."
        self.client = None
        self.retry_ms = 0
        self.idle_ms = 0

    def _connect_wifi(self):
        try:
            if wifi.status():
                self.message = "WiFi OK"
                return True

            wifi.disconnect()
            wifi.connect()
            if wifi.wait():
                self.message = "WiFi OK"
                return True

            self.message = "WiFi failed"
            return False
        except OSError as e:
            self.message = f"WiFi error: {e}"
            return False

    def _connect_mqtt(self):
        try:
            # sim's fake machine module lacks unique_id; real badge has it
            unique = getattr(machine, "unique_id", lambda: b"sim")()
            client_id = b"dogsbody-" + binascii.hexlify(unique)
            self.client = MQTTClient(client_id, "mqtt.emf.camp")
            self.client.connect()
            self.message = "Connected"
            return True
        except (OSError, MQTTException) as e:
            self.message = f"MQTT error: {e}"
            self.client = None
            return False

    def _publish_button(self, name):
        # ponytail: QoS 0 — a press can be lost if the broker dropped an
        # idle connection; one reconnect+retry covers the common case
        topic = TOPIC_BASE + b"/" + name.encode()
        for _ in range(2):
            if self.client is None:
                if not (self._connect_wifi() and self._connect_mqtt()):
                    return
            try:
                self.client.publish(topic, b"pressed")
                self.message = f"Sent {name}"
                return
            except (OSError, MQTTException) as e:
                self.message = f"MQTT error: {e}"
                self.client = None

    def update(self, delta):
        self.idle_ms += delta

        if self.client is None:
            self.retry_ms -= delta
            if self.retry_ms <= 0:
                self.retry_ms = 5000
                if self._connect_wifi():
                    self._connect_mqtt()

        for name in BUTTON_NAMES:
            if self.button_states.get(BUTTON_TYPES[name]):
                self.button_states.clear()
                self.idle_ms = 0
                self._publish_button(name)
                if name == "CANCEL":
                    self.minimise()
                break

    def _reduce_text_until_fits(self, ctx, text, width_limit):
        extra_text = ""
        text_that_fits = text
        while ctx.text_width(text_that_fits) > width_limit and text_that_fits:
            character = text_that_fits[-1]
            text_that_fits = text_that_fits[:-1]
            extra_text = character + extra_text
        return text_that_fits, extra_text

    def _wrap_text(self, ctx, text, width_limit):
        lines = []
        remaining = text
        while remaining:
            line, remaining = self._reduce_text_until_fits(
                ctx, remaining, width_limit
            )
            if not line:
                line = remaining[:1]
                remaining = remaining[1:]
            lines.append(line)
        return lines

    def _draw_dome(self, ctx):
        ctx.line_width = 2
        for color, segs in DOME_SEGMENTS:
            ctx.rgb(*color)
            ctx.begin_path()
            for x1, y1, x2, y2 in segs:
                ctx.move_to(x1, y1)
                ctx.line_to(x2, y2)
            ctx.stroke()

    def draw(self, ctx):
        ctx.save()
        ctx.rgb(0.2, 0, 0).rectangle(-120, -120, 240, 240).fill()

        if self.idle_ms > IDLE_AFTER_MS:
            self._draw_dome(ctx)
            ctx.restore()
            return

        ctx.rgb(1, 1, 1)

        text = f"Message: {self.message}"
        width_limit = 200  # 240px screen minus margins
        lines = self._wrap_text(ctx, text, width_limit)

        spacing = line_height * 16  # scale to your font size
        start_y = -((len(lines) - 1) * spacing) / 2

        for i, line in enumerate(lines):
            y = start_y + i * spacing
            line_width = ctx.text_width(line)
            ctx.move_to(-line_width / 2, y).text(line)

        ctx.restore()


__app_export__ = ThunderdomeApp