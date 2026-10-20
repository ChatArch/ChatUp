from pathlib import Path

from chatenv.configs import OpenAIConfig
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

# Importing CLI/help or planning must not create directories or load credentials.
# Setup commands load typed values when they execute.
OPENAI_API_BASE = OpenAIConfig.OPENAI_API_BASE.value or "https://api.openai.com/v1"
