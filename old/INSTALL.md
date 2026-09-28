# Installation

## Quick Start

```bash
make clone          # 1. Clone repos
cp .env.example .env # 2. Create config
make run           # 3. Build & start
```

Takes ~5 minutes first time.

## Common Issues

**"poetry export does not exist"**
```bash
pipx inject poetry poetry-plugin-export
```

**Docker: not enough space**
```bash
df -h /           # Check disk
make check-diskspace # Run check
```

## Detailed Guide

### 1. Python (pyenv)

```bash
pyenv install 3.13.0
pyenv global 3.13.0
```

### 2. pipx

```bash
pip install pipx
pipx ensurepath
```

### 3. Poetry + plugin

```bash
pipx install poetry
pipx inject poetry poetry-plugin-export
poetry --version
```

### 4. Docker

Download from [docker.com](https://docker.com).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| MYSQL_ROOT_PASSWORD | - | MySQL root |
| MINIO_ROOT_USER | fakekey | S3 access key |
| MINIO_ROOT_PASSWORD | fakesecret | S3 secret key |

## Cheatsheet

```bash
make run    # Start
make stop   # Stop
make build # Build only
make clean # Cleanup
```

## Help?

Need help? Ask in the [Entitybase Telegram group](https://www.wikidata.org/wiki/Wikidata:Tools/Entitybase#Telegram).