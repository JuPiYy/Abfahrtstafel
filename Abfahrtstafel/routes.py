"""
Routes and views for the flask application.
"""
import logging

from flask import render_template

from Abfahrtstafel import app

from Abfahrtstafel.data import news, departures
from Abfahrtstafel.config import settings

logger = settings.logger

@app.route("/")
def start():
    return render_template("index.html", departures=departures(), news=news())