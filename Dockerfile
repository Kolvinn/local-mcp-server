FROM framework-base:latest


COPY --chown=dev:dev ./dev/mcp-server/ /home/dev/app/
USER dev
SHELL ["/bin/bash" , "-c"]

RUN conda install -c conda-forge bun && conda install -c conda-forge uv

# # 2. Install uv and bun
# RUN curl -fsSL https://astral.sh/uv/install.sh | bash
# RUN curl -fsSL https://bun.com/install | bash


# # 3. FIX THE PATH
# # - /root/.local/bin is where 'uv' lives
# # - /root/.bun/bin is where 'bun' lives
# # - /root/app/.venv/bin is where your python environment will live
# # 2. Environment Setup
# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     BUN_INSTALL="/home/dev/.bun" \
#     VIRTUAL_ENV="/home/dev/app/.venv"

# ENV PATH="/home/dev/.local/bin:/home/dev/.bun/bin:/home/dev/app/.venv/bin:$PATH" 



# Now you can use them immediately
WORKDIR /home/dev/app/src
RUN uv --version
RUN bun --version



# 5. Install Dependencies via uv (No local COPY needed)
# This creates the environment and installs the core stack immediately
# Don't do this if you have copied an existing project
# RUN uv init --no-workspace && \
#     uv add fastmcp fastapi uvicorn httpx python-dotenv

# 6. Ensure the environment is synced
RUN uv sync

RUN bun install


# 7. Keep the container alive
# Switch to dev user

CMD ["sleep", "infinity"]