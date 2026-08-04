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
