#!/usr/bin/env python3
import os
import shutil
import sys

ENV_FILE = ".env"
ENV_EXAMPLE = "env.example"
VITE_HOST_KEY = "VITE_HOST"
SETUP_COMPLETED_KEY = "SETUP_COMPLETED"

def main():
    # Check if .env exists
    env_exists = os.path.exists(ENV_FILE)
    
    if env_exists:
        print(f"{ENV_FILE} already exists.")
        response = input("This will overwrite VITE_HOST and SETUP_COMPLETED. Continue? [y/N]: ").strip().lower()
        if response != 'y':
            print("Setup cancelled.")
            sys.exit(0)
        
        # Backup existing .env
        shutil.copy(ENV_FILE, f"{ENV_FILE}.backup")
        print(f"Backed up existing {ENV_FILE} to {ENV_FILE}.backup")
    else:
        if not os.path.exists(ENV_EXAMPLE):
            print(f"Error: {ENV_EXAMPLE} not found.")
            sys.exit(1)
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        print(f"Created {ENV_FILE} from {ENV_EXAMPLE}.")

    # Read existing env vars
    env_vars = {}
    if env_exists:
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

    # Prompt for HOST
    default_host = env_vars.get(VITE_HOST_KEY, 'localhost')
    print(f"\nEnter the server HOST (IP or domain name).")
    print(f"This is used by the frontend to connect to services.")
    print(f"Examples: localhost, 192.168.1.100, example.com")
    host = input(f"HOST [{default_host}]: ").strip()
    if not host:
        host = default_host

    # Update env vars
    env_vars[VITE_HOST_KEY] = host
    env_vars[SETUP_COMPLETED_KEY] = "true"

    # Write back to .env
    with open(ENV_FILE, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    print(f"\nSetup completed!")
    print(f"  VITE_HOST={host}")
    print(f"  SETUP_COMPLETED=true")
    print(f"\nYou can now run 'make run-core'.")

if __name__ == "__main__":
    main()
