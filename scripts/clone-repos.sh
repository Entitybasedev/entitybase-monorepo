#!/bin/bash
set -e

cd "$(dirname "$0")"
cd ..

echo "Creating libs directory..."
mkdir -p libs

python3 - <<'PYTHON'
import yaml
import subprocess
import os

with open("LIBS.yml", "r") as f:
    config = yaml.safe_load(f)

for item in config.get("repos", []):
    name = item["name"]
    url = item["url"]
    target_dir = os.path.join("libs", name)

    if os.path.exists(target_dir):
        pass
    else:
        print(f"Cloning {name}...")
        subprocess.run(["git", "clone", "--depth", "1", url, target_dir], check=True)

print("Done!")
PYTHON
