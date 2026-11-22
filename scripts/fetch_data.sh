#!/usr/bin/env bash
# Download the source dictionaries (jmdict-simplified JSON builds of JMdict + KANJIDIC2).
set -euo pipefail
cd "$(dirname "$0")/../data"
REL="3.6.1%2B20250526122839"
VER="3.6.1+20250526122839"
BASE="https://github.com/scriptin/jmdict-simplified/releases/download/$REL"
curl -sSfL -o jmdict.tgz   "$BASE/jmdict-eng-common-$VER.json.tgz"
curl -sSfL -o kanjidic.tgz "$BASE/kanjidic2-en-$VER.json.tgz"
tar xzf jmdict.tgz && tar xzf kanjidic.tgz
mv -f jmdict-eng-common-*.json jmdict.json
mv -f kanjidic2-en-*.json kanjidic.json
rm -f jmdict.tgz kanjidic.tgz
echo "data ready: $(pwd)"
