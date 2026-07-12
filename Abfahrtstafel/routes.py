"""
Routes and views for the flask application.
"""

from flask import render_template

from Abfahrtstafel import app
from Abfahrtstafel import data

from os import environ

@app.route("/")
def start():
    return render_template("index.html", departures=data.departures(eva_nummer=environ.get("EVA_NUMMER")), news=data.news(eva_nummer=environ.get("EVA_NUMMER")))