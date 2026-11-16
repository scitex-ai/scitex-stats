"""Runtime resolution stays within its declared root before making directories."""

import pytest

from scitex_stats import _runtime_paths as paths


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    root = tmp_path / "runtime"
    root.mkdir()
    monkeypatch.setattr(paths, "STATS_RUNTIME", root)
    return root


@pytest.mark.parametrize("mode", ["absolute", "traversal", "parent_symlink", "file_symlink"])
def test_escaping_paths_fail_before_creating_outside_directories(runtime, tmp_path, mode):
    outside = tmp_path / "outside"
    if mode == "absolute":
        parts = (str(outside / "new" / "result.txt"),)
    elif mode == "traversal":
        parts = ("..", "outside", "new", "result.txt")
    elif mode == "parent_symlink":
        outside.mkdir()
        (runtime / "linked").symlink_to(outside, target_is_directory=True)
        parts = ("linked", "new", "result.txt")
    else:
        (runtime / "result.txt").symlink_to(outside / "result.txt")
        parts = ("result.txt",)
    with pytest.raises(ValueError, match="runtime"):
        paths.runtime_path(*parts)
    if mode == "parent_symlink":
        assert list(outside.iterdir()) == []
    else:
        assert not outside.exists()


def test_nested_paths_keep_lexical_shape_and_create_parent(runtime):
    result = paths.runtime_path("cache", "nested", "result.txt")
    assert result == runtime / "cache/nested/result.txt"
    assert result.parent.is_dir()
    assert not result.exists()


def test_symlinked_runtime_root_remains_supported(runtime, tmp_path, monkeypatch):
    root_link = tmp_path / "configured-root"
    root_link.symlink_to(runtime, target_is_directory=True)
    monkeypatch.setattr(paths, "STATS_RUNTIME", root_link)
    result = paths.runtime_path("cache", "result.txt")
    assert result == root_link / "cache/result.txt"
    assert result.resolve() == runtime / "cache/result.txt"
    assert result.parent.is_dir()


def test_symlink_to_a_directory_within_runtime_is_supported(runtime):
    (runtime / "actual").mkdir()
    (runtime / "alias").symlink_to(runtime / "actual", target_is_directory=True)
    result = paths.runtime_path("alias", "nested", "result.txt")
    assert result == runtime / "alias/nested/result.txt"
    assert result.parent.is_dir()
    assert result.resolve() == runtime / "actual/nested/result.txt"
