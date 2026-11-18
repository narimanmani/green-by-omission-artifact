# Published testmon installation preparation

This directory records installation preparation only. It does not contain a hosted GitHub Actions run, a trusted-baseline execution, or any run of the three original research cases. Those experiments remain `NOT_RUN` until their original snapshots are recovered.

The separate clean environment at `hosted/.venv-testmon` contains the exact requested published package versions. `pip-install.log` records the successful installation; `environment.json` records versions, download provenance and SHA-256 hashes. Each saved testmon Python module is compared byte-for-byte against the verified PyPI wheel. `pytest-help.txt` and `pytest-version.txt` are installation probes, not case results.

To recreate the environment on Windows, run `python -m venv hosted/.venv-testmon`, then install `pytest==9.0.2 pytest-testmon==2.3.0 itsdangerous==2.2.0 starlette==0.50.0 requests==2.32.5 httpx==0.28.1` using that environment's Python. Execute `capture.py` with that same interpreter to refresh provenance. Use a separate clean environment from pytest-depper to avoid cross-plugin effects.

The virtual environment and generated caches are excluded from the deliverable archive. The saved wheel, metadata, source snapshots and logs are reproducibility artifacts.
