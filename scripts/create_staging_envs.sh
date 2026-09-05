#!/bin/bash

# Creates the staging virtualenvs used by the functional tests.
#
# Each server (master, slave, poller, secrets, webui) runs on its own
# virtualenv so that dependency conflicts do not affect each other or the
# integrations venv. (Note: notifications runs in the integrations venv). This script creates (or recreates) the venvs and installs each
# project's latest version from the private package index.
#
# The latest released version of each project is installed via pip using
# --extra-index-url=https://pypi.poraodojuca.dev
#
# Usage:
#   ./scripts/create_staging_envs.sh [PROJECT...]
#
# With no arguments it creates all staging venvs. Pass one or more project
# names to create only those (e.g. ./scripts/create_staging_envs.sh master).

set -e

VENVS_DIR="${VIRTUALENVS_DIR:-$HOME/.virtualenvs}"
INDEX_URL="https://pypi.poraodojuca.dev"

# project -> pip package name / console script
declare -A PACKAGES=(
    [master]="toxicmaster"
    [slave]="toxicslave"
    [poller]="toxicpoller"
    [secrets]="toxicsecrets"
    [webui]="toxicwebui"
)

PYTHON="${PYTHON:-python3}"

projects=("$@")
if [ "${#projects[@]}" -eq 0 ]; then
    projects=("${!PACKAGES[@]}")
fi

for project in "${projects[@]}"; do
    if [ -z "${PACKAGES[$project]+x}" ]; then
        echo "Unknown project '$project'. Valid ones: ${!PACKAGES[@]}" >&2
        exit 1
    fi

    package="${PACKAGES[$project]}"
    venv="$VENVS_DIR/${project}-staging"
    bin="$venv/bin"

    echo "==> Creating venv $venv"
    "$PYTHON" -m venv --clear "$venv"

    echo "==> Installing $package (latest) into $venv"
    "$bin/pip" install -U pip wheel
    "$bin/pip" install --extra-index-url="$INDEX_URL" "$package"

    main_bin="$bin/$package"
    if [ ! -x "$main_bin" ]; then
        echo "Expected binary '$main_bin' was not created after install" >&2
        exit 1
    fi

    echo "==> $project ready at $main_bin"
    echo
done

echo "All staging envs ready."
