FROM ruby:3.2-slim

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    curl \
    nodejs \
    yarn \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN gem install bundler rails

WORKDIR /workspace

EXPOSE 3000

CMD ["/bin/bash"]
