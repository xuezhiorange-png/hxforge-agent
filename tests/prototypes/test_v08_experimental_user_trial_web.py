"""Smoke tests for experimental design web API."""

from __future__ import annotations

from fastapi.testclient import TestClient

from prototypes.v08_thermal_rating.web.server import app

client = TestClient(app)


def test_index_html() -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "HXForge" in r.text


def test_preset_330kw() -> None:
    r = client.get("/api/presets/330kw")
    assert r.status_code == 200
    assert r.json()["target_duty_kw"] == "330"


def test_sync_design_330kw_smoke() -> None:
    preset = client.get("/api/presets/330kw").json()
    preset["max_candidates"] = 24
    preset["run_mdot_verification"] = False
    r = client.post("/api/design/run", json=preset)
    assert r.status_code == 200
    body = r.json()
    assert body.get("rating_engine") == "kernel_v1"
    assert body.get("schema") == "hxforge.kernel-engineering-report.v1"
    assert len(body.get("all_candidates") or []) >= 3
