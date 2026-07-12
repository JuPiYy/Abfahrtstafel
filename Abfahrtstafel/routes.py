"""
Routes and views for the flask application.
"""

from flask import render_template

from Abfahrtstafel import app
from Abfahrtstafel import data

@app.route("/")
def start():
    return render_template("index.html", departures=data.departures(), news=data.news())