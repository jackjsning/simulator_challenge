FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# install gosu for easy step down from root
# https://github.com/tianon/gosu/releases
ENV GOSU_VERSION 1.12
RUN set -ex; \
    savedAptMark="$(apt-mark showmanual)"; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates dirmngr gnupg wget; \
    rm -rf /var/lib/apt/lists/*; \
    dpkgArch="$(dpkg --print-architecture | awk -F- '{ print $NF }')"; \
    wget -O /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch"; \
    wget -O /usr/local/bin/gosu.asc "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch.asc"; \
    export GNUPGHOME="$(mktemp -d)"; \
    # DNS issue with gpg key server requires changing DNS to google dns. Change is only temporary.
    echo "nameserver 8.8.8.8" > /etc/resolv.conf; \ 
    echo "search companydomain" >> /etc/resolv.conf; \    
    gpg --batch --keyserver hkps://keys.openpgp.org --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4; \
    gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu; \
    gpgconf --kill all; \
    rm -rf "$GNUPGHOME" /usr/local/bin/gosu.asc; \
    apt-mark auto '.*' > /dev/null; \
    [ -z "$savedAptMark" ] || apt-mark manual $savedAptMark > /dev/null; \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
    chmod +x /usr/local/bin/gosu; \
    gosu --version; \
    gosu nobody true

RUN apt-get update && apt-get install -y \
    autoconf \
    automake \
    build-essential \
    clang \
    cmake \
    curl \
    git \
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
