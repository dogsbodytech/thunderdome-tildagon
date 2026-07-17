import binascii
import machine

import app
from umqtt.simple import MQTTClient
import wifi

from app_components.tokens import line_height
from events.input import Buttons, BUTTON_TYPES

# mqtt.emf.camp only allows anonymous publish under open/ (2026 policy)
TOPIC = b"open/dogsbody/dome"

class ThunderdomeApp(app.App):
    def __init__(self):
        self.button_states = Buttons(self)
        self.message = "Starting..."
        self.client = None

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
            self.client.publish(TOPIC, b"hello from a sami badge")
            self.message = "Message sent"
            self.client.disconnect()
            return True
        except OSError as e:
            self.message = f"MQTT error: {e}"
            self.client = None
            return False

    def update(self, delta):
        if self.button_states.get(BUTTON_TYPES["CANCEL"]):
            self.button_states.clear()
            self.minimise()
            return

        if self.message == "Starting...":
            if self._connect_wifi():
                self._connect_mqtt()

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

    def draw(self, ctx):
        ctx.save()
        ctx.rgb(0.2, 0, 0).rectangle(-120, -120, 240, 240).fill()
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