from __future__ import annotations

import importlib.util
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "import-resume.py"


def _load_import_resume():
    spec = importlib.util.spec_from_file_location("import_resume", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_format_hh_resume_minimal() -> None:
    mod = _load_import_resume()
    text = mod._format_hh_resume(
        {
            "title": "Python Developer",
            "first_name": "Ivan",
            "last_name": "Petrov",
            "skill_set": ["Python", "PostgreSQL"],
            "experience": [
                {
                    "company": "Acme",
                    "position": "Backend",
                    "start": {"year": 2020, "month": 3},
                    "end": None,
                    "description": "API on FastAPI",
                }
            ],
        }
    )
    assert "Python Developer" in text
    assert "Acme" in text
    assert "FastAPI" in text


def test_fetch_exa_url_parses_results(monkeypatch) -> None:
    mod = _load_import_resume()

    class FakeResp:
        def read(self) -> bytes:
            return json.dumps(
                {"results": [{"text": "# Resume\n\nPython dev"}]}
            ).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a: object) -> None:
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: FakeResp())
    text = mod.fetch_exa_url("https://example.com/resume", "key-test")
    assert "Python dev" in text
