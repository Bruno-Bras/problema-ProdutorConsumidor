#!/usr/bin/env bash
# Dupla: Bruno Barros e Luana Barros. Requer JDK 17 ou superior.
set -euo pipefail
cd -- "$(dirname -- "$0")"
mkdir -p build
javac -encoding UTF-8 --release 17 -d build src/ProdutorConsumidor.java
exec java -cp build ProdutorConsumidor "$@"
