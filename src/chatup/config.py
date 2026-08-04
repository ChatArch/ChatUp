from __future__ import annotations

from chatenv.fields import BaseEnvConfig, EnvField


class CursorAgentConfig(BaseEnvConfig):
    """ChatEnv schema for Cursor Agent credentials used by ChatUp setup."""

    _title = "Cursor Agent"
    _aliases = ["cursor-agent", "cursor_agent", "cursor"]
    _storage_dir = "CursorAgent"

    CURSOR_ACCESS_TOKEN = EnvField(
        "CURSOR_ACCESS_TOKEN",
        desc="Cursor Agent access token copied into Cursor auth.json by chatup cursor-agent.",
        is_sensitive=True,
    )
    CURSOR_REFRESH_TOKEN = EnvField(
        "CURSOR_REFRESH_TOKEN",
        desc="Cursor Agent refresh token copied into Cursor auth.json by chatup cursor-agent.",
        is_sensitive=True,
    )
    CURSOR_CREDENTIAL_STORE = EnvField(
        "CURSOR_CREDENTIAL_STORE",
        default="native",
        desc="Cursor Agent credential store mode: native or file-wrapper.",
    )

    @classmethod
    def test(cls) -> None:
        """Run a non-network schema smoke for chatenv test."""

        print(f"Testing {cls._title}...")
        fields = cls.get_fields()
        expected = {
            "CURSOR_ACCESS_TOKEN",
            "CURSOR_REFRESH_TOKEN",
            "CURSOR_CREDENTIAL_STORE",
        }
        missing = expected.difference(fields)
        if missing:
            raise RuntimeError(f"Missing Cursor Agent config field(s): {', '.join(sorted(missing))}")
        if not fields["CURSOR_ACCESS_TOKEN"].is_sensitive or not fields["CURSOR_REFRESH_TOKEN"].is_sensitive:
            raise RuntimeError("Cursor Agent token fields must be marked sensitive")
        print("✓ Cursor Agent ChatEnv schema is registered.")


class DiscourseAdminConfig(BaseEnvConfig):
    """ChatEnv schema for ChatUp-managed Discourse bootstrap admin credentials."""

    _title = "Discourse Admin"
    _aliases = ["discourse", "discourse-admin", "discourse_admin"]
    _storage_dir = "Discourse"

    DISCOURSE_ADMIN_USERNAME = EnvField(
        "DISCOURSE_ADMIN_USERNAME",
        desc="Initial Discourse administrator username used by ChatUp service setup.",
    )
    DISCOURSE_ADMIN_EMAIL = EnvField(
        "DISCOURSE_ADMIN_EMAIL",
        desc="Initial Discourse administrator email used by ChatUp service setup.",
    )
    DISCOURSE_ADMIN_PASSWORD = EnvField(
        "DISCOURSE_ADMIN_PASSWORD",
        desc="Initial Discourse administrator password used by ChatUp service setup.",
        is_sensitive=True,
    )

    @classmethod
    def test(cls) -> None:
        fields = cls.get_fields()
        expected = {
            "DISCOURSE_ADMIN_USERNAME",
            "DISCOURSE_ADMIN_EMAIL",
            "DISCOURSE_ADMIN_PASSWORD",
        }
        missing = expected.difference(fields)
        if missing:
            raise RuntimeError(f"Missing Discourse admin config field(s): {', '.join(sorted(missing))}")
        if not fields["DISCOURSE_ADMIN_PASSWORD"].is_sensitive:
            raise RuntimeError("Discourse admin password field must be marked sensitive")


class ZulipAdminConfig(BaseEnvConfig):
    """ChatEnv schema for ChatUp-managed Zulip bootstrap admin credentials."""

    _title = "Zulip Admin"
    _aliases = ["zulip", "zulip-admin", "zulip_admin"]
    _storage_dir = "Zulip"

    ZULIP_ADMIN_USERNAME = EnvField(
        "ZULIP_ADMIN_USERNAME",
        desc="Initial Zulip administrator username recorded by ChatUp service setup.",
    )
    ZULIP_ADMIN_EMAIL = EnvField(
        "ZULIP_ADMIN_EMAIL",
        desc="Initial Zulip administrator email used for ZULIP_ADMINISTRATOR.",
    )
    ZULIP_ADMIN_MAIL = EnvField(
        "ZULIP_ADMIN_MAIL",
        desc="Compatibility alias for the initial Zulip administrator email.",
    )
    ZULIP_ADMIN_PASSWORD = EnvField(
        "ZULIP_ADMIN_PASSWORD",
        desc="Initial Zulip administrator password recorded by ChatUp service setup.",
        is_sensitive=True,
    )

    @classmethod
    def test(cls) -> None:
        fields = cls.get_fields()
        expected = {
            "ZULIP_ADMIN_USERNAME",
            "ZULIP_ADMIN_EMAIL",
            "ZULIP_ADMIN_MAIL",
            "ZULIP_ADMIN_PASSWORD",
        }
        missing = expected.difference(fields)
        if missing:
            raise RuntimeError(f"Missing Zulip admin config field(s): {', '.join(sorted(missing))}")
        if not fields["ZULIP_ADMIN_PASSWORD"].is_sensitive:
            raise RuntimeError("Zulip admin password field must be marked sensitive")
