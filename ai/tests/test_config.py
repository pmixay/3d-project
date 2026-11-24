import json

import pytest

from hercules.config import LiveConfig, load


def test_toml_env_and_overrides(tmp_path):
    toml = tmp_path / "c.toml"
    toml.write_text('[camera]\nsource = "/dev/video2"\n[pipeline]\ninterval_s = 5.0\n')
    env = {"HERCULES_STATE_DIR": str(tmp_path / "st"), "HERCULES_PIPELINE__INTERVAL_S": "7",
           "HERCULES_ACTIONS__PAUSE_POLICY": "confirm", "HERCULES_PIPELINE__ROI": "[0.1,0.1,0.9,0.9]"}
    cfg = load(str(toml), env=env)
    assert cfg.camera.source == "/dev/video2"
    assert cfg.pipeline.interval_s == 7.0
    assert cfg.actions.pause_policy == "confirm"
    assert cfg.pipeline.roi == [0.1, 0.1, 0.9, 0.9]

    live = LiveConfig(cfg)
    live.update({"decision": {"warn_threshold": 0.5}, "pipeline": {"interval_s": 2}})
    saved = json.loads((tmp_path / "st" / "settings.json").read_text())
    assert saved == {"decision": {"warn_threshold": 0.5}, "pipeline": {"interval_s": 2.0}}
    again = load(str(toml), env=env)
    assert again.decision.warn_threshold == 0.5 and again.pipeline.interval_s == 2.0


def test_runtime_edit_rejections(tmp_path):
    cfg = load(None, env={"HERCULES_STATE_DIR": str(tmp_path)})
    live = LiveConfig(cfg)
    with pytest.raises(ValueError):
        live.update({"moonraker": {"url": "http://evil"}})      # not editable from the dashboard
    with pytest.raises(ValueError):
        live.update({"pipeline": {"roi": [0.5, 0.5, 0.4, 0.9]}})  # inverted
    with pytest.raises(ValueError):
        live.update({"actions": {"pause_policy": "always"}})
    assert cfg.pipeline.roi == [0.0, 0.0, 1.0, 1.0]               # unchanged after failures


def test_invalid_file_value(tmp_path):
    toml = tmp_path / "c.toml"
    toml.write_text("[pipeline]\nmonitor_when = 'sometimes'\n")
    with pytest.raises(ValueError):
        load(str(toml), env={})
