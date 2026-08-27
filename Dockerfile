FROM python:3.12-slim

# Basic tooling: git for version control inside the container,
# curl/build-essential in case any pip package needs to compile
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install deps at build time if requirements.txt exists yet;
# harmless if it doesn't (container will still start)
COPY requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true
RUN pip install --no-cache-dir google-genai anthropic openai

# Keep the container alive so VS Code can attach to it
CMD ["sleep", "infinity"]
