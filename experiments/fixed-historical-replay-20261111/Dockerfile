FROM python:3.13.13-slim-bookworm@sha256:355bfa66770995d7e9a0da4b3473b44d0cb451f6b56f5615ad9c39e3c4eca03f
LABEL research.scope="fixed-public-historical-regression-replay"
COPY wheels /opt/replay/wheels
COPY requirements-hashed.txt /opt/replay/requirements-hashed.txt
RUN python -m pip install --no-index --find-links=/opt/replay/wheels --require-hashes -r /opt/replay/requirements-hashed.txt --disable-pip-version-check \
    && groupadd --gid 10001 researcher \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin researcher
COPY upstream.zip input-manifest.json PROTOCOL.md /opt/replay/
COPY runtime /opt/replay/runtime
RUN chmod -R a-w /opt/replay
USER 10001:10001
WORKDIR /opt/replay
ENTRYPOINT ["python", "-I", "-B", "/opt/replay/runtime/run_replay.py"]
CMD []
