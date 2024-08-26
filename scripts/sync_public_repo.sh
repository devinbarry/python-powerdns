#!/bin/bash

set -e

# Check for required environment variables
required_vars=("CI_REPOSITORY_URL" "GITHUB_PYTHON_POWERDNS_REPO_URL" "CI_PROJECT_DIR")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: Required environment variable $var is not set."
        exit 1
    fi
done

git clone --single-branch --branch master $CI_REPOSITORY_URL private_repo
cd private_repo
git remote add public $GITHUB_PYTHON_POWERDNS_REPO_URL
git fetch public
git checkout -b temp_branch master

# Construct the absolute path using CI_PROJECT_DIR
SCRIPT_PATH="${CI_PROJECT_DIR}/scripts/parse_gitattributes.py"

# Verify that the script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Error: Script not found at $SCRIPT_PATH"
    exit 1
fi

# Run git filter-branch with the dynamically constructed path
git filter-branch --prune-empty --tree-filter "python3 ${SCRIPT_PATH}" --tag-name-filter cat -- temp_branch

git push -f public temp_branch:master
