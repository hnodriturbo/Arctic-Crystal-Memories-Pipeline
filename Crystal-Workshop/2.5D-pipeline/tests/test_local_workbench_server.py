"""
File: tests/test_local_workbench_server.py
Purpose:
 - Verify local image-preparation options before they reach subprocess commands.
"""

import sys
from pathlib import Path

import pytest

CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from local_workbench_server import load_profiles, normalize_preprocess_options  # noqa: E402


def test_preprocess_defaults_are_safe_for_portrait_geometry() -> None:
    options = normalize_preprocess_options({})
    assert options == {
        "enhance": False,
        "upscale": True,
        "removeBackground": True,
        "alphaMatting": False,
        "removeBgModel": "isnet-general-use",
        "upscaleTarget": 2048,
    }


def test_preprocess_accepts_full_local_recipe() -> None:
    options = normalize_preprocess_options(
        {
            "options": {
                "enhance": True,
                "upscale": True,
                "removeBackground": True,
                "alphaMatting": True,
                "removeBgModel": "birefnet-portrait",
                "upscaleTarget": 4096,
            }
        }
    )
    assert options["enhance"] is True
    assert options["alphaMatting"] is True
    assert options["removeBgModel"] == "birefnet-portrait"
    assert options["upscaleTarget"] == 4096


def test_preprocess_rejects_unbounded_or_unknown_choices() -> None:
    with pytest.raises(ValueError, match="Unknown background-removal model"):
        normalize_preprocess_options({"options": {"removeBgModel": "../../model"}})
    with pytest.raises(ValueError, match="2048 or 4096"):
        normalize_preprocess_options({"options": {"upscaleTarget": 12000}})


def test_deep_cuda_profile_is_explicit_and_runnable() -> None:
    profiles = {profile["id"]: profile for profile in load_profiles()}
    deep_profile = profiles["cuda-quality-deep"]
    assert deep_profile["runnable"] is True
    assert "20 mm" in deep_profile["environment"]
