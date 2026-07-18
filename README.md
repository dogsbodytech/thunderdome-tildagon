# Thunderdome

Control the Thunderdome — Dogsbody's geodesic dome with 5000 LEDs — from your EMF Camp Tildagon badge.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## About

Thunderdome is a [Tildagon](https://tildagon.badge.emfcamp.org/) badge app so anyone can control the Thunderdome!

## Installation

Install **Thunderdome** from the badge app store (Apps → categories → Games).

Or copy it straight to a connected badge with [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html):

```sh
./install-on-badge.py
```

### Requirements

- A Tildagon (2024) or Spaceagon (2026) badge.
- Emfcamp Wi-Fi configured on the badge (for MQTT).

## Development

The app runs in the [badge simulator](https://github.com/emfcamp/badge-2024-software).
Symlink this repo into the sim's `apps/` directory and launch the sim:

```sh
ln -s /path/to/thunderdome /path/to/badge-2024-software/sim/apps/thunderdome
```

Runtime files live at the repo root (`app.py`, `dome.py`, `effects/`,
`__init__.py`, `metadata.json`); `tildagon.toml` carries the app-store metadata.
Dev/tooling files are kept out of the badge download via `.gitattributes`
(`export-ignore`).

## Publishing

Bump `version` in `tildagon.toml`, push, tag `vX.Y.Z`, and create a matching
GitHub release on a repo tagged with the `tildagon-app` topic. The app appears in
the store ~15 minutes later. See the
[publish docs](https://tildagon.badge.emfcamp.org/tildagon-apps/publish/).

## Acknowledgments

Built for [Electromagnetic Field](https://emfcamp.org/) and the Tildagon badge.

## License

Thunderdome is licensed under the MIT license. See [`LICENSE`](LICENSE) for details.
