export OLLAMA_MODEL_TRIAGE := gemma2:2b
export OLLAMA_MODEL_ESCALATE := gemma2:2b

.PHONY: install run run-apply test eval lint voice digest snooze resolve install-systemd

PYTHON ?= python3
PY ?= .venv/bin/python

install:
	$(PYTHON) -c "import sys; sys.exit('Python 3.11 or newer is required') if sys.version_info < (3, 11) else None"
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e ".[dev]"

run:
	$(PY) run.py --dir $(HOME)/Downloads

run-apply:
	$(PY) run.py --dir $(HOME)/Downloads --apply

test:
	.venv/bin/python -m pytest

eval:
	.venv/bin/python eval/run_eval.py

lint:
	.venv/bin/ruff check .

voice:
	mkdir -p $(HOME)/.local/share/nothingtodo
	-piper --download-dir $(HOME)/.local/share/nothingtodo --voice en_US-lessac-medium || echo "Piper voice download failed — will fall back to espeak-ng"

digest:
	$(PY) run.py --digest

snooze:
	@test -n "$(ID)" || (echo "Usage: make snooze ID=3" && exit 1)
	$(PY) run.py --snooze $(ID)

resolve:
	@test -n "$(ID)" || (echo "Usage: make resolve ID=3" && exit 1)
	$(PY) run.py --resolve $(ID)

install-systemd:
	mkdir -p $(HOME)/.config/systemd/user
	cp systemd/nothingtodo.service systemd/nothingtodo.timer $(HOME)/.config/systemd/user/
	systemctl --user daemon-reload
	systemctl --user enable --now nothingtodo.timer
	@echo "Timer installed. Check: systemctl --user list-timers nothingtodo"
