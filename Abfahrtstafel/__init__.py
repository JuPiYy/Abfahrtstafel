"""
The flask application package.
"""

from flask import Flask

from Abfahrtstafel.config import settings

app = Flask(__name__)

from Abfahrtstafel import routes

__all__ = ["app", "settings"]
