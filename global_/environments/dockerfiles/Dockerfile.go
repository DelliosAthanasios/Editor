FROM golang:1.21-alpine

RUN apk add --no-cache \
    git \
    curl \
    build-base

RUN go install github.com/cosmtrek/air@latest 2>/dev/null || true && \
    go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest 2>/dev/null || true

WORKDIR /workspace

ENV GOPATH=/workspace/go

CMD ["/bin/sh"]
