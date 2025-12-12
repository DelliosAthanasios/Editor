FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    sbcl \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN curl -O https://beta.quicklisp.org/quicklisp.lisp 2>/dev/null && \
    sbcl --non-interactive --load quicklisp.lisp \
    --eval '(quicklisp-quickstart:install)' 2>/dev/null || true && \
    rm -f quicklisp.lisp

WORKDIR /workspace

CMD ["/bin/bash"]
