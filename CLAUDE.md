# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

This repository is in its initial/scaffolding stage — no commits yet, no application code. Current contents:

- `Pipfile` — Pipenv config, Python 3.13.3, no packages declared yet.
- `dome-mqtt-broker/` — empty directory, presumably intended to hold an MQTT broker component.

## Environment

- Python dependency management is via **Pipenv** (`Pipfile`, no `Pipfile.lock` yet).
  - Install deps: `pipenv install`
  - Add a package: `pipenv install <package>`
  - Run a command in the env: `pipenv run <command>`
  - Activate a shell: `pipenv shell`

There is no build, lint, or test tooling configured yet. Update this file once source code, dependencies, and tooling are added.
