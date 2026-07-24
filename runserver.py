"""
This script runs the Abfahrtstafel application using a development server.
"""
import logging

from Abfahrtstafel import app, settings

logger = settings.logger

if __name__ == '__main__':
    app.run(settings.host, settings.port)
