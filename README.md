# OpenRelik Worker - SSDeep

## Description

The **OpenRelik SSDeep Worker** is a Celery-based task processor designed to calculate SSDeep (Context-Triggered Piecewise Hashes) for files. SSDeep is a fuzzy hashing algorithm used to identify similar files, even if they have minor modifications.

**Key Functionalities:**
*   Accepts one or more input files.
*   For each input file, it executes the `ssdeep` command-line tool.
*   Generates an output file (e.g., `original_filename.ssdeep`) for each input, containing the calculated SSDeep hash. If a file is too small for SSDeep or an error occurs, the output file will contain a relevant notice or error message.

## Deploy
Add the below configuration to the OpenRelik docker-compose.yml file.

```
openrelik-worker-ssdeep:
    container_name: openrelik-worker-ssdeep
    image: ghcr.io/openrelik/openrelik-worker-ssdeep:latest
    restart: always
    environment:
      - REDIS_URL=redis://openrelik-redis:6379
      - OPENRELIK_PYDEBUG=0
    volumes:
      - ./data:/usr/share/openrelik/data
    command: "celery --app=src.app worker --task-events --concurrency=4 --loglevel=INFO -Q openrelik-worker-ssdeep"
    # ports:
      # - 5678:5678 # For debugging purposes.
```

## Test
```
pip install poetry
poetry install --with test --no-root
poetry run pytest --cov=. -v
```
