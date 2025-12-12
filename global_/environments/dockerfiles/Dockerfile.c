FROM gcc:latest

RUN apt-get update && apt-get install -y \
    gdb \
    make \
    cmake \
    valgrind \
    git \
    curl \
    build-essential \
    clang \
    clang-format \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["/bin/bash"]
