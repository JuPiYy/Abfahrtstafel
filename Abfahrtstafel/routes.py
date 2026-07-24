"""
Routes and views for the flask application.
"""
import logging

from flask import render_template

from Abfahrtstafel import app, data, settings

logger = settings.logger

@app.route("/")
def start():
    return render_template("index.html", departures=data.departures(), news=data.news())