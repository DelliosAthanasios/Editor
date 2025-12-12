FROM gcc:latest

RUN apt-get update && apt-get install -y \
    g++ \
    gdb \
    make \
    cmake \
    git \
    curl \
    build-essential \
    clang \
    clang-format \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["/bin/bash"]
