FROM python:3.12 as base

ENV WORKDIR=/app \
    CONFIG=/config/settings.yaml \
    LOG_LEVEL=ERROR \
    LOG_FILE=/config/logs/plejd.log \
    LOG_FILE_HC=/config/logs/healthcheck.log

RUN apt-get update \
  && apt-get --no-install-recommends install -y bluez=5.66-1 bluetooth=5.66-1 \
  && rm -rf /var/lib/apt/lists/* \
  && adduser --disabled-password --gecos '' plejd

WORKDIR  $WORKDIR
RUN chown plejd:plejd $WORKDIR

# Start building stage
FROM base as builder

USER plejd

RUN pip install --no-cache-dir --user poetry==1.7.1

# Ensure the poetry command is available
ENV PATH="/home/plejd/.local/bin:${POETRY_HOME}/bin:${PATH}"

# Copy poetry files
COPY poetry.lock pyproject.toml README.md $WORKDIR/

# Copy application files
COPY ./plejd_mqtt_ha $WORKDIR/plejd_mqtt_ha

# Install and build dependencies using poetry
RUN poetry config virtualenvs.in-project true && \
    poetry install --only=main --no-root && \
    poetry build

# Start final stage
FROM base as final

RUN adduser plejd bluetooth

ENV PYTHONPATH="$WORKDIR/.venv/lib/python3.12/site-packages:${PYTHONPATH}"

# Copy the built virtualenv deps from the builder stage
COPY --from=builder /app/.venv $WORKDIR/.venv
COPY --from=builder /app/dist $WORKDIR/
COPY docker-entrypoint.sh $WORKDIR/

RUN ./.venv/bin/pip install "$WORKDIR"/*.whl

# Healthcheck
COPY healthcheck.py $WORKDIR/healthcheck.py
HEALTHCHECK --interval=1m --timeout=1s \
  CMD su plejd -c "python healthcheck.py" || exit 1

# Set the entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]
