from pathlib import Path

from chatenv.configs import OpenAIConfig
from chatenv.fields import BaseEnvConfig
from chatenv.paths import get_paths

# ChatTool 7.0.0 uses the ChatArch env root directly. Old platformdirs based
# paths are intentionally not used as fallback.
CHATARCH_PATHS = get_paths()
CHATARCH_HOME = CHATARCH_PATHS.home_dir
CHATARCH_ENV_DIR = CHATARCH_PATHS.envs_dir
CHATARCH_ENV_FILE = CHATARCH_ENV_DIR / ".env"
CHATARCH_CACHE_DIR = CHATARCH_HOME / "cache" / "chatup"
CHATARCH_CONFIG_DIR = CHATARCH_HOME / "config" / "chatup"
CHATTOOL_REPO_DIR = Path(__file__).parent.parent.parent

CHATARCH_ENV_DIR.mkdir(parents=True, exist_ok=True)
CHATARCH_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# setup environment variables
# explicit args > environment > typed env files > default values
BaseEnvConfig.load_all(CHATARCH_ENV_DIR)

# Inject loaded values into current namespace for setup modules that read constants.
globals().update(BaseEnvConfig.get_all_values())

_api_base = globals().get("OPENAI_API_BASE")

# Final fallback
if not _api_base:
    _api_base = "https://api.openai.com/v1"

OPENAI_API_BASE = _api_base
# Update the config object as well, just in case
OpenAIConfig.OPENAI_API_BASE.value = _api_base
