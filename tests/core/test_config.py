"""Tests for chico.core.config."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from chico.core.config import (
    Config,
    PolicyConfig,
    ProviderConfig,
    SourceConfig,
    load_config,
)


def _write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(data))
    return path


@pytest.fixture()
def config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("chico.core.config.CONFIG_FILE", tmp_path / "config.yaml")
    return tmp_path / "config.yaml"


# ---------------------------------------------------------------------------
# SourceConfig
# ---------------------------------------------------------------------------


class TestSourceConfig:
    def test_required_fields(self):
        s = SourceConfig(name="s", type="github", repo="org/repo", path="configs/")
        assert s.name == "s"
        assert s.repo == "org/repo"
        assert s.path == "configs/"

    def test_branch_defaults_to_main(self):
        s = SourceConfig(name="s", type="github", repo="org/repo", path="configs/")
        assert s.branch == "main"

    def test_token_env_defaults_to_github_token(self):
        s = SourceConfig(name="s", type="github", repo="org/repo", path="configs/")
        assert s.token_env == "GITHUB_TOKEN"

    def test_source_prefix_defaults_to_empty(self):
        s = SourceConfig(name="s", type="github", repo="org/repo", path="configs/")
        assert s.source_prefix == ""

    def test_target_defaults_to_empty(self):
        s = SourceConfig(name="s", type="github", repo="org/repo", path="configs/")
        assert s.target == ""

    def test_custom_values(self):
        s = SourceConfig(
            name="kiro-configs",
            type="github",
            repo="org/kiro-config",
            path="configs/",
            branch="develop",
            token_env="MY_TOKEN",
            source_prefix="configs/",
            target="kiro",
        )
        assert s.branch == "develop"
        assert s.token_env == "MY_TOKEN"
        assert s.source_prefix == "configs/"
        assert s.target == "kiro"


# ---------------------------------------------------------------------------
# ProviderConfig
# ---------------------------------------------------------------------------


class TestProviderConfig:
    def test_required_fields(self):
        p = ProviderConfig(name="kiro", type="kiro")
        assert p.name == "kiro"
        assert p.type == "kiro"

    def test_level_defaults_to_global(self):
        p = ProviderConfig(name="kiro", type="kiro")
        assert p.level == "global"

    def test_project_level(self):
        p = ProviderConfig(name="kiro", type="kiro", level="project")
        assert p.level == "project"

    def test_path_defaults_to_empty(self):
        p = ProviderConfig(name="kiro", type="kiro")
        assert p.path == ""

    def test_path_stored_when_set(self):
        p = ProviderConfig(
            name="kiro", type="kiro", level="project", path="/my/project"
        )
        assert p.path == "/my/project"


# ---------------------------------------------------------------------------
# PolicyConfig
# ---------------------------------------------------------------------------


class TestPolicyConfig:
    def test_strategy_defaults_to_safe(self):
        assert PolicyConfig().strategy == "safe"

    def test_custom_strategy(self):
        assert PolicyConfig(strategy="auto").strategy == "auto"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_empty_config(self):
        config = Config(providers=[], sources=[], policy=PolicyConfig())
        assert config.providers == []
        assert config.sources == []

    def test_get_provider_by_name(self):
        p = ProviderConfig(name="kiro", type="kiro")
        config = Config(providers=[p], sources=[], policy=PolicyConfig())
        assert config.get_provider("kiro") is p

    def test_get_provider_returns_none_when_missing(self):
        config = Config(providers=[], sources=[], policy=PolicyConfig())
        assert config.get_provider("missing") is None

    def test_get_source_by_name(self):
        s = SourceConfig(name="kiro-configs", type="github", repo="org/repo", path="c/")
        config = Config(providers=[], sources=[s], policy=PolicyConfig())
        assert config.get_source("kiro-configs") is s

    def test_get_source_returns_none_when_missing(self):
        config = Config(providers=[], sources=[], policy=PolicyConfig())
        assert config.get_source("missing") is None

    def test_filter_by_source_returns_filtered_config(self):
        s1 = SourceConfig(name="hooks", type="github", repo="org/r1", path="h/")
        s2 = SourceConfig(name="steering", type="github", repo="org/r2", path="s/")
        p = ProviderConfig(name="kiro", type="kiro")
        config = Config(providers=[p], sources=[s1, s2], policy=PolicyConfig())
        filtered = config.filter_by_source("hooks")
        assert len(filtered.sources) == 1
        assert filtered.sources[0].name == "hooks"
        assert filtered.providers == [p]

    def test_filter_by_source_raises_when_not_found(self):
        from chico.core.config import ConfigValidationError

        s = SourceConfig(name="hooks", type="github", repo="org/r", path="h/")
        config = Config(providers=[], sources=[s], policy=PolicyConfig())
        with pytest.raises(ConfigValidationError, match="missing"):
            config.filter_by_source("missing")

    def test_filter_by_source_error_lists_available(self):
        from chico.core.config import ConfigValidationError

        s1 = SourceConfig(name="hooks", type="github", repo="org/r1", path="h/")
        s2 = SourceConfig(name="steering", type="github", repo="org/r2", path="s/")
        config = Config(providers=[], sources=[s1, s2], policy=PolicyConfig())
        with pytest.raises(ConfigValidationError, match="hooks, steering"):
            config.filter_by_source("nope")


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_loads_full_config(self, config_file: Path):
        _write_config(
            config_file.parent,
            {
                "providers": [{"name": "kiro", "type": "kiro", "level": "global"}],
                "sources": [
                    {
                        "name": "kiro-configs",
                        "type": "github",
                        "repo": "org/kiro-config",
                        "path": "configs/",
                        "branch": "main",
                        "token_env": "GITHUB_TOKEN",
                        "source_prefix": "configs/",
                        "target": "kiro",
                    }
                ],
                "policy": {"strategy": "safe"},
            },
        )
        config = load_config()
        assert len(config.providers) == 1
        assert len(config.sources) == 1
        assert config.providers[0].name == "kiro"
        assert config.sources[0].repo == "org/kiro-config"
        assert config.policy.strategy == "safe"

    def test_loads_provider_defaults(self, config_file: Path):
        _write_config(
            config_file.parent,
            {
                "providers": [{"name": "kiro", "type": "kiro"}],
                "sources": [],
                "policy": {"strategy": "safe"},
            },
        )
        config = load_config()
        assert config.providers[0].level == "global"
        assert config.providers[0].path == ""

    def test_loads_provider_with_path(self, config_file: Path):
        _write_config(
            config_file.parent,
            {
                "providers": [
                    {
                        "name": "kiro",
                        "type": "kiro",
                        "level": "project",
                        "path": "/home/user/my-project",
                    }
                ],
                "sources": [],
                "policy": {"strategy": "safe"},
            },
        )
        config = load_config()
        assert config.providers[0].level == "project"
        assert config.providers[0].path == "/home/user/my-project"

    def test_loads_source_defaults(self, config_file: Path):
        _write_config(
            config_file.parent,
            {
                "providers": [],
                "sources": [
                    {"name": "s", "type": "github", "repo": "org/r", "path": "p/"}
                ],
                "policy": {"strategy": "safe"},
            },
        )
        config = load_config()
        s = config.sources[0]
        assert s.branch == "main"
        assert s.token_env == "GITHUB_TOKEN"
        assert s.source_prefix == ""
        assert s.target == ""

    def test_empty_providers_and_sources(self, config_file: Path):
        _write_config(
            config_file.parent,
            {
                "providers": [],
                "sources": [],
                "policy": {"strategy": "safe"},
            },
        )
        config = load_config()
        assert config.providers == []
        assert config.sources == []

    def test_raises_when_config_file_missing(self, config_file: Path):
        from chico.core.config import ConfigNotFoundError

        with pytest.raises(ConfigNotFoundError):
            load_config()

    def test_raises_when_source_missing_required_field(self, config_file: Path):
        _write_config(
            config_file.parent,
            {
                "providers": [],
                "sources": [{"name": "s", "type": "github"}],  # missing repo and path
                "policy": {"strategy": "safe"},
            },
        )
        from chico.core.config import ConfigValidationError

        with pytest.raises(ConfigValidationError):
            load_config()

    def test_multiple_sources(self, config_file: Path):
        _write_config(
            config_file.parent,
            {
                "providers": [],
                "sources": [
                    {"name": "s1", "type": "github", "repo": "org/r1", "path": "p/"},
                    {"name": "s2", "type": "github", "repo": "org/r2", "path": "p/"},
                ],
                "policy": {"strategy": "safe"},
            },
        )
        config = load_config()
        assert len(config.sources) == 2
        assert config.get_source("s1").repo == "org/r1"
        assert config.get_source("s2").repo == "org/r2"
