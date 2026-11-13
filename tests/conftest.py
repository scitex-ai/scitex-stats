"""Pin the test root without modifying interpreters or caller state.

Subprocess tracing is configured in pyproject.toml through coverage.py's
subprocess patch. The dev extra requires its packaged startup hook and
pytest-cov's compatible integration. Test collection must not install .pth
files or overwrite caller-owned coverage configuration.
"""
