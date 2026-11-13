# Frozen shared lifecycle fixture

`dev-owned-context.bash.fixture` is an unmodified test snapshot of
[scitex-dev owned_context.sh](https://github.com/scitex-ai/scitex-dev/blob/41b907f7f32069fcf42855bf5a7722875e29cbec/src/scitex_dev/ci/owned_context.sh).
Its SHA-256 is `a795678455d409e076a1c93a4a810b50c89499fcb83ae4c90a8d31a19e90e5d1`.
The wrapper checks that fixed upstream digest before sourcing it. This fixture
keeps unit tests offline; production callers stage the qualified upstream
resource explicitly. The runtime wrapper does not default to this test file.
The source owner remains scitex-dev (AGPL-3.0-only); update the snapshot and
consumer pin together only after qualifying a new upstream revision.
