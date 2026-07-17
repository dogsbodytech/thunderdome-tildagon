import binascii
import machine

import app
from umqtt.simple import MQTTClient, MQTTException
import wifi

from app_components.tokens import line_height
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus

# mqtt.emf.camp only allows anonymous publish under open/ (2026 policy)
TOPIC_BASE = b"open/dogsbody/dome"


# MicroPython has no enum module, so a constants class is the badge-safe
# equivalent of an Enum/Select. Values double as MQTT topic leaf names.
class DomeControl:
    UP = "UP"
    RIGHT = "RIGHT"
    CONFIRM = "CONFIRM"
    DOWN = "DOWN"
    LEFT = "LEFT"
    CANCEL = "CANCEL"
    TOUCH01 = "TOUCH01"
    TOUCH02 = "TOUCH02"
    TOUCH03 = "TOUCH03"
    TOUCH04 = "TOUCH04"
    TOUCH05 = "TOUCH05"
    TOUCH06 = "TOUCH06"
    TOUCH07 = "TOUCH07"
    TOUCH08 = "TOUCH08"
    TOUCH09 = "TOUCH09"
    TOUCH10 = "TOUCH10"
    TOUCH11 = "TOUCH11"
    TOUCH12 = "TOUCH12"
    LEFTPROX = "LEFTPROX"
    RIGHTPROX = "RIGHTPROX"


# One colour per strut class, index-matched to DOME_SEGMENTS.
DOME_COLORS = {
    "classic": ((1.0, 0.2, 0.2), (0.25, 0.4, 1.0)),
    "ember": ((1.0, 0.6, 0.1), (0.9, 0.2, 0.1)),
    "mono": ((1.0, 1.0, 1.0), (0.55, 0.55, 0.55)),
}

# 2V geodesic hemisphere wireframe, precomputed from dome/Assembly.drawio.svg
# geometry (2V = 2 strut classes; source 3V had a third). One tuple of
# segments per strut class. Screen-space coords centred on (0, 0), 240x240.
DOME_SEGMENTS = (
    (
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
    ),
    (
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
    ),
)


class ThunderdomeApp(app.App):
    def __init__(self):
        # Input events require focus (InputEvent.requires_focus), so this
        # handler never fires while minimised — no remove/re-add needed.
        eventbus.on(ButtonDownEvent, self._on_button_down, self)
        self.status = "Connecting"
        self.dome_colors = DOME_COLORS["classic"]
        self.client = None
        self.retry_ms = 0

    def _connect_wifi(self):
        try:
            if wifi.status():
                return True

            wifi.disconnect()
            wifi.connect()
            if wifi.wait():
                return True

            self.status = "WiFi failed"
            return False
        except OSError as e:
            self.status = f"WiFi error: {e}"
            return False

    def _connect_mqtt(self):
        try:
            # sim's fake machine module lacks unique_id; real badge has it
            unique = getattr(machine, "unique_id", lambda: b"sim")()
            client_id = b"dogsbody-" + binascii.hexlify(unique)
            self.client = MQTTClient(client_id, "mqtt.emf.camp")
            self.client.connect()
            self.status = "Connected"
            return True
        except (OSError, MQTTException) as e:
            self.status = f"MQTT error: {e}"
            self.client = None
            return False

    def _publish_button(self, name):
        # Sets self.status on failure, returns True on success so the
        # caller can set its own per-button status text.
        # ponytail: QoS 0 — a press can be lost if the broker dropped an
        # idle connection; one reconnect+retry covers the common case
        topic = TOPIC_BASE + b"/" + name.encode()
        for _ in range(2):
            if self.client is None:
                if not (self._connect_wifi() and self._connect_mqtt()):
                    return False
            try:
                self.client.publish(topic, b"pressed")
                return True
            except (OSError, MQTTException) as e:
                self.status = f"MQTT error: {e}"
                self.client = None
        return False

    def update(self, delta):
        if self.client is None:
            self.retry_ms -= delta
            if self.retry_ms <= 0:
                self.retry_ms = 5000
                if self._connect_wifi():
                    self._connect_mqtt()

    def _on_button_down(self, event):
        # MicroPython has no match/case; if/elif chain is the select
        if BUTTON_TYPES["UP"] in event.button:
            if self._publish_button(DomeControl.UP):
                self.status = "Sent UP"

        elif BUTTON_TYPES["RIGHT"] in event.button:
            if self._publish_button(DomeControl.RIGHT):
                self.status = "Sent RIGHT"

        elif BUTTON_TYPES["CONFIRM"] in event.button:
            if self._publish_button(DomeControl.CONFIRM):
                self.status = "Sent CONFIRM"

        elif BUTTON_TYPES["DOWN"] in event.button:
            if self._publish_button(DomeControl.DOWN):
                self.status = "Sent DOWN"

        elif BUTTON_TYPES["LEFT"] in event.button:
            if self._publish_button(DomeControl.LEFT):
                self.status = "Sent LEFT"

        elif BUTTON_TYPES["CANCEL"] in event.button:
            if self._publish_button(DomeControl.CANCEL):
                self.status = "Sent CANCEL"
            self.minimise()

        elif event.button.name == "TOUCH01":
            if self._publish_button(DomeControl.TOUCH01):
                self.status = "Sent TOUCH01"

        elif event.button.name == "TOUCH02":
            if self._publish_button(DomeControl.TOUCH02):
                self.status = "Sent TOUCH02"

        elif event.button.name == "TOUCH03":
            if self._publish_button(DomeControl.TOUCH03):
                self.status = "Sent TOUCH03"

        elif event.button.name == "TOUCH04":
            if self._publish_button(DomeControl.TOUCH04):
                self.status = "Sent TOUCH04"

        elif event.button.name == "TOUCH05":
            if self._publish_button(DomeControl.TOUCH05):
                self.status = "Sent TOUCH05"

        elif event.button.name == "TOUCH06":
            if self._publish_button(DomeControl.TOUCH06):
                self.status = "Sent TOUCH06"

        elif event.button.name == "TOUCH07":
            if self._publish_button(DomeControl.TOUCH07):
                self.status = "Sent TOUCH07"

        elif event.button.name == "TOUCH08":
            if self._publish_button(DomeControl.TOUCH08):
                self.status = "Sent TOUCH08"

        elif event.button.name == "TOUCH09":
            if self._publish_button(DomeControl.TOUCH09):
                self.status = "Sent TOUCH09"

        elif event.button.name == "TOUCH10":
            if self._publish_button(DomeControl.TOUCH10):
                self.status = "Sent TOUCH10"

        elif event.button.name == "TOUCH11":
            if self._publish_button(DomeControl.TOUCH11):
                self.status = "Sent TOUCH11"

        elif event.button.name == "TOUCH12":
            if self._publish_button(DomeControl.TOUCH12):
                self.status = "Sent TOUCH12"

        # elif event.button.name == "LEFTPROX":
        #     if self._publish_button(DomeControl.LEFTPROX):
        #         self.status = "Sent LEFTPROX"

        # elif event.button.name == "RIGHTPROX":
        #     if self._publish_button(DomeControl.RIGHTPROX):
        #         self.status = "Sent RIGHTPROX"

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
        for color, segs in zip(self.dome_colors, DOME_SEGMENTS):
            ctx.rgb(*color)
            ctx.begin_path()
            for x1, y1, x2, y2 in segs:
                ctx.move_to(x1, y1)
                ctx.line_to(x2, y2)
            ctx.stroke()

    def draw(self, ctx):
        ctx.save()
        ctx.rgb(0.2, 0, 0).rectangle(-120, -120, 240, 240).fill()

        self._draw_dome(ctx)

        ctx.rgb(1, 1, 1)
        spacing = line_height * 16  # scale to your font size
        y = 82  # below the dome; round screen narrows here
        for line in self._wrap_text(ctx, self.status, 140):
            line_width = ctx.text_width(line)
            ctx.move_to(-line_width / 2, y).text(line)
            y += spacing

        ctx.restore()


__app_export__ = ThunderdomeApp
