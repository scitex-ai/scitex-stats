# Opt-in native CI tests

The existing `ci` workflow keeps its normal Python matrix, import, quality and
Sphinx jobs. A manual dispatch can additionally select `native_test_profile`.
Its default is false; pushes, pull requests and schedules do not select this job.
The job inherits no secrets and grants only contents read permission.

The additional job calls the pinned shared leaf test workflow with the current
workflow source commit. Shared admission checks the original trusted actor
allowlist and matching triggering actor identity. The Stats profile binds
compute-03, the measured
image/runtime bytes, all ten leaf helpers and the immutable Dev lifecycle
resource. The complete Python 3.11–3.13 matrix runs sequentially, preserving the
owning all/dev installation, worker policy and coverage. Each job has the
original 30-minute limit, including resource staging and cleanup.

The required v1.0.0 test-plan label creates no Git tag or package. The shared
Stats registry refuses build and publish operations before native scheduling.
The existing private 1.0.0 artifacts remain NEVER_UPLOAD. Version selection,
main promotion, release tags, archive/public-install checks and publisher trust
are separate requirements.

A prepared caller or passing workflow syntax does not establish successful
execution. Inspect the original dispatch admission, actual resource staging,
three complete suite logs, leaf cleanup and bootstrap cleanup before accepting
integration.
