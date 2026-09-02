# Reddi Arena — preview deployment
# Runs the same web/server.py used locally. No build step, no framework.
FROM python:3.12-slim

WORKDIR /app

# PyYAML parses the ADL documents; jsonschema powers the validation gate.
# solders derives real Solana PDAs for the On-Chain projection tab.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY web/ ./web/
COPY adl/ ./adl/
COPY tools/ ./tools/
COPY vendor/ ./vendor/
# The Devnet Preview is off unless an operator sets
# REDDI_ENABLE_SOLANA_DEVNET_ASSURANCE_PREVIEW, but its deterministic fixtures
# must be in the image so enabling it serves the preview instead of a fixture
# integrity 500. They are data only — no key, wallet, or live-rail material.
COPY fixtures/assurance/ ./fixtures/assurance/

# Ephemeral by default. Mount a Railway volume and set DATA_DIR=/data to make
# the leaderboard and waitlist survive redeploys.
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["python3", "web/server.py"]
