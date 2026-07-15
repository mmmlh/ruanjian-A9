import importlib


def test_backend_app_module_is_importable_from_repo_root():
    module = importlib.import_module("app.main")

    assert module is not None
