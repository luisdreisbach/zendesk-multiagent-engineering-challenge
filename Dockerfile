ARG REGISTRY=docker.io/library
FROM ${REGISTRY}/python:3.13.3-slim-bullseye

# Add system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates make \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1
ENV UV_INSTALL_DIR="/usr/local/uv/"

# Download the latest installer
ADD https://astral.sh/uv/0.5.0/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh ./uv-installer.sh && rm ./uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="$PATH:$UV_INSTALL_DIR"
ENV PYTHONPATH=${PYTHONPATH}:/usr/src/app

WORKDIR /usr/src

COPY pyproject.toml uv.lock ./

# Install project dependencies
RUN uv sync

COPY app/ ./app/

COPY Makefile ./

CMD ["make", "start"]

