FROM ubuntu:22.04

RUN apt update && apt install -y \
    cmake \
    ninja-build \
    g++ \
    git \
    python3 \
    python3-pip \
    python3-venv \
    libzstd-dev \
    libjemalloc-dev \
    pkg-config \
    libicu-dev \
    clang-format \
    libssl-dev \
    perl \
    ca-certificates \
    make \
    libssl-dev \
    zlib1g-dev \
    libnghttp2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN git config --global http.version HTTP/1.1

RUN cmake -S . -B build -G Ninja \
  -DUSERVER_FEATURE_TESTSUITE=OFF

RUN cmake --build build

CMD ["./build/wall_service", "--config", "configs/static_config.yaml"]