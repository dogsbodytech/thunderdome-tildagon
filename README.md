# Thunderdome

A Tildagon badge app that publishes button, joystick and touch-strip presses
over MQTT to `mqtt.emf.camp`, under `open/dogsbody/dome/<CONTROL>`, to drive the
Thunderdome geodesic dome. It also renders a wireframe of the dome on screen.

## Install on a badge

App store: install "Thunderdome" from the badge app store.

Manually (mpremote):

```sh
./install-on-badge.py
```

## Develop

The app runs in the [badge simulator](https://github.com/emfcamp/badge-2024-software).
Symlink this repo into `sim/apps/` and launch the sim.

## Publish

`tildagon.toml` holds the app-store metadata. To release: bump `version`, push,
tag `vX.Y.Z`, and create a matching GitHub release on a repo tagged with the
`tildagon-app` topic. See the
[publish docs](https://tildagon.badge.emfcamp.org/tildagon-apps/publish/).
