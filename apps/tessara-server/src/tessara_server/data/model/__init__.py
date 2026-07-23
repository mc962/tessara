"""Importing this package registers all models with SQLAlchemy's mapper
registry — needed so cross-model relationships (User.api_tokens <->
ApiToken.user) can resolve their string-based forward references regardless
of which module happens to be imported first."""

from tessara_server.data.model.api_token import ApiToken
from tessara_server.data.model.user import User

__all__ = ["ApiToken", "User"]
