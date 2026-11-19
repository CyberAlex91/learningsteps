# Zweck: Stellt die geprüfte Nutzeridentität als FastAPI-Abhängigkeit bereit.
"""The production authentication dependency shared by every protected route."""

from security.identity import AuthSettings, create_current_user_dependency

auth_settings = AuthSettings.load()
current_user = create_current_user_dependency(auth_settings)
