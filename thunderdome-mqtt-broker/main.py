import paho.mqtt.client as mqtt

BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC = "dogsbody"


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"connected: {reason_code}")
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    handle_dogsbody_event(payload)


def handle_dogsbody_event(payload):
    # TODO: parse payload (json?)
    # TODO: dispatch to dome hardware/action
    # TODO: log/persist event
    print(f"[{TOPIC}] {payload}")


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT)
    client.loop_forever()


if __name__ == "__main__":
    main()
