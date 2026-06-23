"""ChatUp config compatibility exports.

ChatEnv owns the shared ChatArch env schemas. ChatUp depends on
``chatenv>=0.2.0,<0.3.0`` and re-exports the shared config classes here only so
setup modules can keep importing ``chatup.config`` without forking schema
fields.
"""

from chatenv.configs import FeishuConfig, OpenAIConfig
from chatenv.fields import BaseEnvConfig, EnvField, normalize_profile_name

__all__ = [
    "EnvField",
    "BaseEnvConfig",
    "normalize_profile_name",
    "OpenAIConfig",
    "FeishuConfig",
]
