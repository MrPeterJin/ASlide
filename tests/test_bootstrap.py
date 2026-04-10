from __future__ import annotations

import importlib
import os
from pathlib import Path


def test_bootstrap_module_exposes_runtime_helpers() -> None:
    from Aslide.bootstrap import (
        collect_library_paths,
        preload_shared_libraries,
        setup_runtime_environment,
    )

    assert callable(collect_library_paths)
    assert callable(preload_shared_libraries)
    assert callable(setup_runtime_environment)


def test_collect_library_paths_discovers_vendor_lib_dirs() -> None:
    from Aslide.bootstrap import collect_library_paths

    paths = collect_library_paths()
    path_set = {Path(path) for path in paths}

    assert Path(__file__).resolve().parents[1] / "Aslide" / "opencv" / "lib" in path_set
    assert Path(__file__).resolve().parents[1] / "Aslide" / "sdpc" / "lib" in path_set


def test_setup_runtime_environment_is_explicit(monkeypatch) -> None:
    monkeypatch.setenv("LD_LIBRARY_PATH", "baseline")

    import Aslide

    importlib.reload(Aslide)
    assert os.environ["LD_LIBRARY_PATH"] == "baseline"

    from Aslide.bootstrap import collect_library_paths, setup_runtime_environment

    paths = collect_library_paths()
    setup_runtime_environment(paths)

    ld_library_path = os.environ["LD_LIBRARY_PATH"]
    assert "baseline" in ld_library_path
    assert any(path in ld_library_path for path in paths)


def test_install_script_no_longer_mentions_shell_profile_updates() -> None:
    setup_path = Path(__file__).resolve().parents[1] / "setup.py"
    setup_source = setup_path.read_text()

    assert "Updated shell configuration file" not in setup_source
    assert "shell_config_files" not in setup_source
    assert "ld.so.conf.d" not in setup_source
    assert "aslide-paths.pth" not in setup_source
    assert 'version="' in setup_source
