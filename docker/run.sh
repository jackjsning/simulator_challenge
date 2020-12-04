#!/bin/bash
set -e

PROJECT_DIR=$(git rev-parse --show-toplevel)
. $PROJECT_DIR/.env
cd $PROJECT_DIR

function run_built_shell() {
    docker run --network=host \
        -it \
        -e LOCAL_USER_ID=$USER_ID \
        --rm \
        -v $PROJECT_DIR:$DOCKER_PROJECT_DIR \
        $BUILT:$BUILT_TAG \
        bash
}

function run_built() {
    docker run --network=host \
        -t \
        -e LOCAL_USER_ID=$USER_ID \
        --rm \
        -v $PROJECT_DIR:$DOCKER_PROJECT_DIR \
        $DOCKER_REGISTRY/$DOCKER_ORG/$BUILT:$BUILT_TAG \
        $@
}

case $1 in
    built)
        run_built ${@:2}
        ;;
    built_shell)
        run_built_shell
        ;;
    *)
        echo "not supported argument"
        ;;
esac
