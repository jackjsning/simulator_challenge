FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    autoconf \
    automake \
    build-essential \
    clang \
    cmake \
    curl \
    git \
    gosu \
    g++ \
    libbz2-dev \
    libffi-dev \
    liblzma-dev \
    libncurses5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    libxml2-dev \
    libxmlsec1-dev \
    llvm \
    locales \
    make \
    python3-dev \
    python3-pip \
    tk-dev \
    wget \
    xz-utils \
    zlib1g-dev

ARG DOCKER_PROJECT_DIR
RUN mkdir ${DOCKER_PROJECT_DIR}
WORKDIR ${DOCKER_PROJECT_DIR}
COPY . .

RUN pip3 install -r docker/requirements.txt
RUN pip3 install -e .

COPY docker/entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["entrypoint.sh"]
