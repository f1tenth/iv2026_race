#!/usr/bin/env bash
# Serves the Jekyll site locally at http://localhost:4000
#
# Prerequisites (one-time setup if not already installed):
#   1. Install Ruby dev headers:
#        sudo apt install ruby-dev
#   2. Install Jekyll and Bundler to your user directory:
#        gem install bundler jekyll --user-install
#   3. Add the gem bin dir to your PATH (add this line to ~/.bashrc, then restart terminal):
#        export PATH="$HOME/.local/share/gem/ruby/3.0.0/bin:$PATH"

set -e

cd "$(dirname "$0")/.."

export PATH="$HOME/.local/share/gem/ruby/3.0.0/bin:$PATH"

bundle config set --local path vendor/bundle
bundle install
bundle exec jekyll serve --livereload
