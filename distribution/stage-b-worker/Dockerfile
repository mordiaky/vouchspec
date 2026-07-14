FROM python:3.11-slim@sha256:f9fa7f851e38bfb19c9de3afbc4b86ae7176ea7aaf94535c31df5458d5849457

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY distribution/github-action/requirements-linux-x86_64-py311.lock /tmp/requirements.lock
RUN python -m pip install --only-binary=:all: --require-hashes -r /tmp/requirements.lock \
    && rm -rf /root/.cache /tmp/requirements.lock

WORKDIR /app
COPY src/capabilityproof /app/capabilityproof
RUN chmod -R a-w /app

USER 65532:65532
ENTRYPOINT ["python", "-I", "-c", "import sys;sys.path.insert(0,'/app');from capabilityproof.stage_b_worker import main;raise SystemExit(main())"]
