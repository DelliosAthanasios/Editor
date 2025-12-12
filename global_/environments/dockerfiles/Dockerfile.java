FROM openjdk:17-slim

RUN apt-get update && apt-get install -y \
    maven \
    gradle \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

ENV JAVA_HOME=/usr/local/openjdk-17

EXPOSE 8080 8443 5005

CMD ["/bin/bash"]
