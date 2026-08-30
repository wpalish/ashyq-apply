# ASHYQ Apply — API and worker share this image; the command differs.
#
# Multi-stage: the builder holds the toolchain, the runtime holds only what is
# needed to serve. Runs as a non-root user with no shell.

FROM python:3.12-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Dependencies are copied and installed before the source, so a code change
# does not invalidate the dependency layer.
COPY requirements.txt ./
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH="/ms-playwright" \
    UNIMATCH_ENVIRONMENT=production \
    UNIMATCH_AUTO_MIGRATE=false

# curl is for the container healthcheck only.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 10001 ashyq \
 && useradd --system --uid 10001 --gid ashyq --home /app --shell /usr/sbin/nologin ashyq

COPY --from=builder /opt/venv /opt/venv
# Live research escalates JavaScript-only pages to Chromium. Installing it in
# the image makes that tier real in containers instead of silently unavailable.
RUN playwright install --with-deps chromium \
 && chmod -R a+rX /ms-playwright
WORKDIR /app
COPY --chown=ashyq:ashyq . .

# The commit this image was built from. Reported by /api/health and recorded on
# every job, so a stalled queue names the two builds that disagreed. Without it
# every build reported "0.1.0" and two disagreeing builds looked identical.
ARG ASHYQ_BUILD_SHA=""
ENV ASHYQ_BUILD_SHA=${ASHYQ_BUILD_SHA}

# Writable only where it must be.
RUN mkdir -p /app/data && chown -R ashyq:ashyq /app/data

USER ashyq
EXPOSE 8099

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8099/api/health || exit 1

# Overridden by the worker service in compose.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099"]
