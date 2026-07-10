FROM astral/uv:python3.12-bookworm-slim AS builder

# Install system deps to build bitcoin-kernel
RUN apt update -qqy \
   && apt -y install \
   bison \
   build-essential \
   cmake \
   curl \
   g++ \
   git \
   libboost-dev  \
   make \
   ninja-build \
   ninja-build \
   patch \
   pkgconf \
   python3 \
   ripgrep \
   xz-utils

WORKDIR /workshop

COPY pyproject.toml .
COPY uv.lock .

RUN touch README.md && \
    uv sync && \
    echo '\nsource /workshop/.venv/bin/activate' >> ~/.bashrc

FROM builder AS demo

COPY . .

ENTRYPOINT [ "bash" ]
