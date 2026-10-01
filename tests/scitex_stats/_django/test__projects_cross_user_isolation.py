#!/usr/bin/env python3
"""Cross-user isolation: another user's rows stay invisible through every read path.

Fleet standard (operator-ordered, routed by the Applications Lead): a row owned
by user A must not be reachable by user B through ANY read path of this app.
Named for the module that owns the seams (``_django/_projects.py``), which is
what this file mirrors.

WHERE THE ENFORCEMENT LIVES. This app has no row-level permission table of its
own — it is project-scoped, and the HOST owns scope and authorization (the
scitex-app contract). So the two seams every read and write has to pass are:

    data scope   ``_projects.authorized_project(project_id, request)`` — the
                 provider is asked WITH the request, so the listing it returns
                 IS the data scope for that caller; an id it does not list for
                 THIS caller has no directory at all (fail-closed, no fallback
                 to a same-named local folder).
    ``can()``    ``_projects.can_write(project_id, request)`` — a capability
                 SEPARATE from the listing, because the hub lists read-only
                 collaborators too and a listing is not write authority.

``can()`` itself is not shipped by scitex-app yet: ``scitex_app.authz`` says in
its own words that "``can()`` IS NOT HERE YET" and ships only the Verdict value
it will return — and 0.26.1 is the latest release. So until the SDK lands it,
the request-aware pair above IS this app's implementation of the same rule, and
these tests pin the isolation AT those seams rather than waiting on the SDK.

BOTH SEAMS ARE PINNED INDEPENDENTLY, which is why the stub host has THREE
users: ``bob`` is listed nothing (his refusal could come from either seam),
while ``carol`` IS listed alice's project and still may not write it — so her
case fails if only the data-scope seam refuses and the write seam is permissive.

THE STUB HOST. A hub-shaped provider lists a project only to the users it
authorizes, and a separate storage capability says where that project's files
live and whether this caller may write. Caller identity arrives the way it does
in production — an authentication middleware sets ``request.user`` (here from an
``X-Test-User`` header) — and every read path is driven through the app's real
urlconf.

READ PATHS COVERED, i.e. everything that can carry a project's rows:
  * ``GET /`` — the page, whose context carries the active project's file list;
  * ``GET /api/project-scope`` — the picker's listing + the resolved current id;
  * ``POST /api/project-scope`` — the picker's remember, which echoes the id;
  * ``GET /api/project-files`` — the active project's file listing;
  * ``GET /api/project-import`` — one file's TEXT: the rows themselves.
The other routes (``api/run``, ``api/plot``, ``api/report/*``, …) are stateless:
they compute from numbers posted in the body and read no project, so there is no
row of another user's for them to disclose.

Test-style notes: one assertion per test with Arrange/Act/Assert markers (the
repo's STX-TQ convention), and each assertion compares ONE observation mapping
against its expected value so a failure names the path that leaked. Project
roots are redirected by ENVIRONMENT, the knob a real deployment sets — PA-306
forbids mocks, and nothing here patches an object: the app's own views, provider
resolution and urlconf all run.
"""

from __future__ import annotations

import contextlib
import importlib
import json
import os
import pathlib

import pytest

pytest.importorskip("django")
pytest.importorskip("scitex_sdk")
importlib.import_module('scitex_sdk.app')
pytest.importorskip("scitex_sdk")
importlib.import_module('scitex_sdk.ui')

from django.test import Client, RequestFactory, override_settings  # noqa: E402
from django.utils.module_loading import import_string  # noqa: E402
from scitex_sdk.ui.project_scope import ProjectEntry  # noqa: E402

from scitex_stats._django import _projects  # noqa: E402

from .test_views import client  # noqa: E402,F401  (shared Django bootstrap)

ALICE = "alice"
BOB = "bob"
CAROL = "carol"
ALICE_PID = "alice-cohort"
BOB_PID = "bob-cohort"
ALICE_FILE = "alice-rows.csv"
BOB_FILE = "bob-rows.csv"
# Values that appear in exactly one user's file, so a leak is a string match
# rather than an inference from a shape.
ALICE_ONLY = "987654321.5"
BOB_ONLY = "112233445.5"

#: Who may SEE each project, and which of them may WRITE it — the hub's own
#: read-only-collaborator shape, which is why the two seams are separate.
ACCESS = {
    ALICE_PID: {ALICE: True, CAROL: False},
    BOB_PID: {BOB: True},
}

#: The knob a deployment (or this suite) uses to say where the host's projects are.
ROOT_ENV = "SCITEX_STATS_TEST_HUB_ROOT"
#: The header the stub authentication middleware reads the caller from.
CALLER_HEADER = "X-Test-User"


def _root() -> pathlib.Path:
    return pathlib.Path(os.environ[ROOT_ENV])


def _caller_name(request) -> str:
    """The caller's name as the app sees it: ``request.user``, or ""."""
    user = getattr(request, "user", None)
    if not getattr(user, "is_authenticated", False):
        return ""
    return str(getattr(user, "username", "") or "")


class _User:
    """A signed-in user, shaped like the one the host's middleware attaches."""

    def __init__(self, username: str) -> None:
        self.username = username
        self.is_authenticated = True
        self.pk = abs(hash(username)) % 10000


class _CallerMiddleware:
    """Stand-in for the host's authentication middleware: sets ``request.user``.

    Registered by dotted path in ``MIDDLEWARE`` (see :func:`_hub`), which is how
    a real host makes a caller visible to a leaf app — and why the provider can
    answer per caller without the app handing it a user itself.
    """

    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request):
        name = request.headers.get(CALLER_HEADER, "")
        if name:
            request.user = _User(name)
        return self.get_response(request)


class _TwoOwnerHubProvider:
    """Hub-shaped provider: the LISTING is the data scope, per request.

    ``last_visited`` is deliberately GLOBAL — the sloppiest thing a host could
    do — so the tests prove the app does not depend on the host scoping that
    pointer by user: ``resolve_project`` re-checks any stored id against the
    caller's own listing and refuses it otherwise.
    """

    def __init__(self) -> None:
        self.last_visited_id = None

    def list_projects(self, request=None):
        who = _caller_name(request)
        return [
            ProjectEntry(id=pid, name=pid, detail="/".join(sorted(ACCESS[pid])))
            for pid in ACCESS
            if who in ACCESS[pid]
        ]

    def last_visited(self, request=None):
        return self.last_visited_id

    def remember(self, request, project_id):
        self.last_visited_id = str(project_id)


class _TwoOwnerHubStorage:
    """Where an authorized project's files live, and whether THIS caller may write.

    A class (not an instance) because that is the documented registration form:
    ``SCITEX_PROJECT_STORAGE`` names a dotted path and the app instantiates it.
    """

    def project_path(self, project_id, request=None):
        owner = ALICE if str(project_id) == ALICE_PID else BOB if str(project_id) == BOB_PID else None
        return _root() / owner / str(project_id) if owner else None

    def can_write(self, project_id, request=None):
        return ACCESS.get(str(project_id), {}).get(_caller_name(request)) is True


_hub_provider = _TwoOwnerHubProvider()
_PROVIDER_PATH = f"{__name__}._hub_provider"
_STORAGE_PATH = f"{__name__}._TwoOwnerHubStorage"
_MIDDLEWARE_PATH = f"{__name__}._CallerMiddleware"


@contextlib.contextmanager
def _projects_root(path):
    """Point the stub host's project root at ``path`` (env, restored after)."""
    previous = os.environ.get(ROOT_ENV)
    os.environ[ROOT_ENV] = str(path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(ROOT_ENV, None)
        else:
            os.environ[ROOT_ENV] = previous


@contextlib.contextmanager
def _hub(path):
    """Register the stub host: per-caller listing + storage, and a caller middleware.

    A fresh ``Client`` built INSIDE this block loads the middleware chain from
    the overridden settings (Django builds it lazily, on a Client's first
    request), so identity reaches the app the way it does in production without
    touching the shared settings the other test modules configured.
    """
    settings_kwargs = {
        "SCITEX_PROJECT_PROVIDER": _PROVIDER_PATH,
        "SCITEX_PROJECT_STORAGE": _STORAGE_PATH,
        "MIDDLEWARE": [
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            _MIDDLEWARE_PATH,
        ],
    }
    with _projects_root(path), override_settings(**settings_kwargs):
        yield


def _seed_projects(root: pathlib.Path) -> None:
    """Give each user one project holding one data file, with a private value."""
    for owner, project, name, value in (
        (ALICE, ALICE_PID, ALICE_FILE, ALICE_ONLY),
        (BOB, BOB_PID, BOB_FILE, BOB_ONLY),
    ):
        directory = root / owner / project
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(f"a,b\n1.0,{value}\n", "utf-8")


def _client_for(name: str) -> Client:
    """One caller, one client — the same app, distinct identities."""
    return Client(headers={CALLER_HEADER: name})


def _artifact_names(root: pathlib.Path, project: str) -> list[str]:
    """The artifacts alice's project holds — the only ones a write may leave."""
    return sorted(p.name for p in (root / ALICE / project / "stats" / "results").glob("*.json"))


def _carries(payload: str, needles) -> list[str]:
    """Which of ``needles`` this response text carries — [] is the clean answer."""
    return [needle for needle in needles if needle in payload]


# ---------------------------------------------------------------------------
# The fleet standard: another user's rows are invisible on every read path.
# ---------------------------------------------------------------------------


def test_cross_user_isolation_no_read_path_shows_rows_owned_by_another_user(tmp_path):
    # Arrange: alice's project exists and holds a value no other fixture carries.
    root = tmp_path / "hub"
    _seed_projects(root)
    with _hub(root):
        bob = _client_for(BOB)
        # Act: bob addresses ALICE's project explicitly — the hostile caller's
        # strongest move, since every other shape resolves no project at all.
        page = bob.get(f"/?project={ALICE_PID}")
        listing = bob.get("/api/project-scope")
        remember = bob.post(
            "/api/project-scope",
            data=json.dumps({"id": ALICE_PID}),
            content_type="application/json",
        )
        files = bob.get(f"/api/project-files?project={ALICE_PID}")
        imported = bob.get(f"/api/project-import?project={ALICE_PID}&name={ALICE_FILE}")
        # The control: the SAME probes carry bob's own rows, so a clean
        # observation means refusal rather than an app that answers nothing.
        own = bob.get(f"/api/project-import?project={BOB_PID}&name={BOB_FILE}")
        observed = {
            "GET / status": page.status_code,
            "GET / carries": _carries(page.content.decode(), (ALICE_ONLY, ALICE_FILE, ALICE_PID)),
            "GET /api/project-scope carries": _carries(listing.content.decode(), (ALICE_PID, ALICE_FILE)),
            "POST /api/project-scope status": remember.status_code,
            "GET /api/project-files status": files.status_code,
            "GET /api/project-files carries": _carries(files.content.decode(), (ALICE_FILE,)),
            "GET /api/project-import status": imported.status_code,
            "GET /api/project-import carries": _carries(imported.content.decode(), (ALICE_ONLY,)),
            "bob's own rows (control)": (own.status_code, _carries(own.content.decode(), (BOB_ONLY,))),
        }
    # Assert: no read path carried alice's rows to bob, and the control carried
    # bob's own (200 + his value) — the refusals above mean refusal.
    assert observed == {
        "GET / status": 200,
        "GET / carries": [],
        "GET /api/project-scope carries": [],
        "POST /api/project-scope status": 403,
        "GET /api/project-files status": 403,
        "GET /api/project-files carries": [],
        "GET /api/project-import status": 403,
        "GET /api/project-import carries": [],
        "bob's own rows (control)": (200, [BOB_ONLY]),
    }


def test_cross_user_isolation_another_users_last_visited_project_never_resolves(tmp_path):
    # Arrange: the hub remembers ALICE's project as the last visited one — the
    # hostile case, in which the pointer itself belongs to the other user.
    root = tmp_path / "hub"
    _seed_projects(root)
    provider = import_string(_PROVIDER_PATH)
    provider.last_visited_id = ALICE_PID
    try:
        with _hub(root):
            bob = _client_for(BOB)
            # Act: bob makes the two requests that consult the stored pointer.
            picker = json.loads(bob.get("/api/project-scope").content.decode())
            rendered = bob.get("/").content.decode()
        # Assert: the stored id never resolves for another caller.
        assert picker["current"] is None and ALICE_PID not in rendered
    finally:
        provider.last_visited_id = None


# The data-scope seam, as bob (authorized nothing) meets it: each entry maps his
# request to the value that means "this project is not yours".
_SEAMS = {
    "authorized_project": (lambda request: _projects.authorized_project(ALICE_PID, request), None),
    "can_write": (lambda request: _projects.can_write(ALICE_PID, request), False),
    "list_data_files": (lambda request: _projects.list_data_files(ALICE_PID, request), None),
    "read_data_file": (lambda request: _projects.read_data_file(ALICE_PID, ALICE_FILE, request), None),
    "save_artifact": (
        lambda request: _projects.save_artifact(ALICE_PID, "results", "result.json", {"a": 1}, request=request),
        None,
    ),
}


@pytest.mark.parametrize("seam", list(_SEAMS))
def test_cross_user_isolation_the_data_scope_and_can_write_seams_refuse_another_users_project(tmp_path, seam):
    # Arrange
    root = tmp_path / "hub"
    _seed_projects(root)
    request = RequestFactory().get("/")
    request.user = _User(BOB)
    answer, refused_value = _SEAMS[seam]
    with _hub(root):
        # Act
        observed = answer(request)
    # Assert
    assert observed == refused_value


def test_cross_user_isolation_a_listed_reader_still_cannot_write_another_users_project(tmp_path):
    # Arrange: carol IS authorized to see alice's project — so only the write
    # seam can refuse her. Without her, a permissive can() would be invisible:
    # bob's refusal comes from the data scope before can() is ever asked.
    root = tmp_path / "hub"
    _seed_projects(root)
    request = RequestFactory().get("/")
    request.user = _User(CAROL)
    url = f"/api/project-save?project={ALICE_PID}"
    payload = json.dumps({"project": ALICE_PID, "kind": "results", "name": "result.json", "payload": {"a": 1}})
    with _hub(root):
        carol = _client_for(CAROL)
        # Act
        listed = _projects.authorized_project(ALICE_PID, request)
        verdict = _projects.can_write(ALICE_PID, request)
        saved = _projects.save_artifact(ALICE_PID, "results", "result.json", {"a": 1}, request=request)
        refused = carol.post(url, data=payload, content_type="application/json")
        observed = {
            "she is on alice's listing": listed is not None,
            "can_write verdict": verdict,
            "save_artifact result": saved,
            "POST /api/project-save status": refused.status_code,
            "artifacts alice owns": _artifact_names(root, ALICE_PID),
        }
    # Assert: she is genuinely listed (so the refusal is can()'s own work), and
    # neither the capability nor the route let her write into alice's project.
    assert observed == {
        "she is on alice's listing": True,
        "can_write verdict": False,
        "save_artifact result": None,
        "POST /api/project-save status": 403,
        "artifacts alice owns": [],
    }


def test_cross_user_isolation_a_write_addressed_to_another_users_project_is_refused(tmp_path):
    # Arrange: alice's project IS writable by alice, so only the caller check
    # can refuse bob — the SAME url is posted by both callers.
    root = tmp_path / "hub"
    _seed_projects(root)
    payload = json.dumps({"project": ALICE_PID, "kind": "results", "name": "result.json", "payload": {"a": 1}})
    url = f"/api/project-save?project={ALICE_PID}"
    with _hub(root):
        alice, bob = _client_for(ALICE), _client_for(BOB)
        # Act
        alice_own = alice.post(url, data=payload, content_type="application/json")
        refused = bob.post(url, data=payload, content_type="application/json")
        observed = {
            "alice's own write": alice_own.status_code,
            "bob's write": refused.status_code,
            "artifacts in her project": _artifact_names(root, ALICE_PID),
        }
    # Assert: alice's write landed, bob's did not, and his attempt added nothing.
    assert observed == {"alice's own write": 201, "bob's write": 403, "artifacts in her project": ["result.json"]}


# EOF
