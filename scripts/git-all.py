#!/usr/bin/env python3
import yaml
import subprocess
import sys
import os

os.chdir(os.path.join(os.path.dirname(__file__), ".."))

with open("LIBS.yml", "r") as f:
    config = yaml.safe_load(f)

action = sys.argv[1] if len(sys.argv) > 1 else "status"

for item in config.get("repos", []):
    name = item["name"]
    target_dir = os.path.join("libs", name)

    if not os.path.exists(target_dir):
        continue

    print(f"{name}:")
    if action == "push":
        subprocess.run(["git", "-C", target_dir, "push"])
    elif action == "pull":
        subprocess.run(["git", "-C", target_dir, "pull"])
    else:
        subprocess.run(["git", "-C", target_dir, "status", "--short"])
