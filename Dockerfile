
# Use the latest Python 3 slim image
FROM python:3-slim


# 3. Install Dev Tools
# Since you'll be editing inside, we add vim/nano and git
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    unzip \
    vim \
    procps \
    && rm -rf /var/lib/apt/lists/*



# Copy the script into the image
COPY ./scripts/init-user.sh /tmp/init-user.sh
# Run the script and then remove it to keep the layer clean
RUN chmod +x /tmp/init-user.sh && \
    /tmp/init-user.sh && \
    rm /tmp/init-user.sh
# 4. Initialize Workspace
WORKDIR /home/dev/app
COPY ./dev/mcp-server/main.py .
RUN chmod dev:dev main.py
USER dev
# 2. Install uv and bun
RUN curl -fsSL https://astral.sh/uv/install.sh | bash
RUN curl -fsSL https://bun.com/install | bash

# 3. FIX THE PATH
# - /root/.local/bin is where 'uv' lives
# - /root/.bun/bin is where 'bun' lives
# - /root/app/.venv/bin is where your python environment will live
# 2. Environment Setup
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BUN_INSTALL="/home/dev/.bun" \
    VIRTUAL_ENV="/home/dev/app/.venv" \
    PATH="/home/dev/.local/bin:/home/dev/.bun/bin:/home/dev/app/.venv/bin:$PATH"


# Now you can use them immediately
RUN uv --version
RUN bun --version



# 5. Install Dependencies via uv (No local COPY needed)
# This creates the environment and installs the core stack immediately
RUN uv init --no-workspace && \
    uv add fastmcp fastapi uvicorn httpx python-dotenv

# 6. Ensure the environment is synced
RUN uv sync

RUN bun init -y

# 7. Keep the container alive
# Switch to dev user

CMD ["sleep", "infinity"]