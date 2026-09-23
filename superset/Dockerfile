# Superset + the Postgres driver (the official docs' recommended way to add drivers).
FROM apache/superset:5.0.0
USER root
RUN . /app/.venv/bin/activate && uv pip install psycopg2-binary
USER superset
