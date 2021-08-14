#!/bin/bash
set -e

PROJECT_DIR=$(git rev-parse --show-toplevel)
. $PROJECT_DIR/.env
cd $PROJECT_DIR

function build_container() {
    build_docker $BUILT $BUILT_TAG docker/Dockerfile --build-arg DOCKER_PROJECT_DIR
}

function build_docker() {
    IMAGE=$1
    TAG=$2
    DOCKERFILE=$3
    BUILD_ARGS=${@:4}

    docker build -t $IMAGE:$TAG $BUILD_ARGS -f $DOCKERFILE .
}

case $1 in
    container)
        build_container
        ;;
    *)
        echo "not supported argument"
        ;;
esac
