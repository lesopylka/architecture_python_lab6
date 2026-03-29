FROM userver-base

WORKDIR /app
COPY . .

RUN cmake -S . -B build -G Ninja \
    -DUSERVER_FEATURE_TESTSUITE=OFF \
    -DUSERVER_FEATURE_CURL=OFF

RUN cmake --build build -j2

CMD ["./build/wall_service", "--config", "configs/static_config.yaml"]