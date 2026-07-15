from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_plugin_manifests_have_required_contract_fields() -> None:
    for plugin_id in ("hk_bus_core", "hk_bus_arrival"):
        manifest = json.loads((ROOT / plugin_id / "plugin.json").read_text(encoding="utf-8"))
        assert manifest["tesserae_compat"] == "1.x"
        assert manifest["version"] == "0.1.0"
        assert manifest["supports"]["sizes"] == ["xs", "sm", "md", "lg"]
        assert manifest["requires"] == ["network:data.etabus.gov.hk"]


def test_arrival_widget_uses_saved_journey_choices() -> None:
    manifest = json.loads(
        (ROOT / "hk_bus_arrival" / "plugin.json").read_text(encoding="utf-8")
    )
    journey_option = next(
        option for option in manifest["cell_options"] if option["name"] == "journey_id"
    )
    assert journey_option["type"] == "multiselect"
    assert journey_option["default"] == []
    assert journey_option["choices_from"] == "journeys"


def test_arrival_widget_offers_font_size_choices() -> None:
    manifest = json.loads(
        (ROOT / "hk_bus_arrival" / "plugin.json").read_text(encoding="utf-8")
    )
    font_option = next(
        option for option in manifest["cell_options"] if option["name"] == "font_size"
    )

    assert font_option["type"] == "select"
    assert font_option["default"] == "normal"
    assert [choice["value"] for choice in font_option["choices"]] == [
        "small",
        "normal",
        "large",
        "extra_large",
    ]
