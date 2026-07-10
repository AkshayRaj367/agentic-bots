#!/bin/bash

# Usage: ./setup.sh [groq]
# If you pass the argument "groq" or set USE_GROQ=1, the script will
# install the groq-only requirements file to avoid installing other LLMs.

REQ_FILE="requirements.txt"
if [ "$1" = "groq" ] || [ "$USE_GROQ" = "1" ]; then
	REQ_FILE="requirements-groq.txt"
	echo "Using groq-only requirements: $REQ_FILE"
else
	echo "Using full requirements: $REQ_FILE"
fi

pip3 install -r "$REQ_FILE"
playwright install
python3 -m playwright install-deps
cd ui/ || exit 1
# Prefer bun if available, otherwise fall back to npm
if command -v bun >/dev/null 2>&1; then
	bun install
else
	if command -v npm >/dev/null 2>&1; then
		npm install
	else
		echo "Warning: neither bun nor npm found. Skipping UI install."
	fi
fi
