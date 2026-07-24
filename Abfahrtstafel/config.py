import logging 

from os import environ

class Settings():
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.host = environ.get("HOST") if environ.get("HOST") else "localhost"
        self.port = int(environ.get("PORT")) if environ.get("PORT") else 5555

        api_base_url = environ.get("API_BASE_URL")
        legacy_base_url = environ.get("BASE_URL")

        if api_base_url:
            self.api_base_url = api_base_url.rstrip('/')
        elif legacy_base_url:
            legacy = legacy_base_url.rstrip('/')
            self.api_base_url = legacy.rsplit('/fchg', 1)[0] if '/fchg' in legacy else legacy
        else:
            self.api_base_url = "https://iris.noncd.db.de/iris-tts/timetable"

        self.plan_base_url = f"{self.api_base_url}/plan"
        self.fchg_base_url = f"{self.api_base_url}/fchg"

        self.eva_nummer = environ.get("EVA_NUMMER") if environ.get("EVA_NUMMER") else "8005580"

        if not environ.get("EVA_NUMMER"):
            self.logger.warning(f"Achtung, aktuell ist keine Bahnhofs-ID definiert! Falle zurück auf: {self.eva_nummer} (Sinzig (Rhein))")  # Default: Sinzig

settings = Settings()