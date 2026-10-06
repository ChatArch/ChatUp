def test_glance_start_command_uses_typed_provider_bridge(monkeypatch, tmp_path):
    from chatup.setup import glance
    monkeypatch.setattr(glance.platform, "system", lambda: "Linux")
    monkeypatch.setattr(glance.platform, "machine", lambda: "amd64")
    result = glance.install_glance(home=tmp_path / "runtime", dry_run=True)
    assert result.start_command == ("chatglance", "runtime", "serve", "--runtime-home", str(tmp_path / "runtime"))
