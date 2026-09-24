"""
The flask application package.
"""

import logging

from flask import Flask

from Abfahrtstafel.config import settings

logger = settings.logger

app = Flask(__name__)

from Abfahrtstafel.routes import start