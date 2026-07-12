"""
Routes and views for the flask application.
"""

from flask import render_template

from Abfahrtstafel import app
from Abfahrtstafel import data

@app.route('/departures')
def departures():
    return data.departures()

@app.route('/news')
def news():
    return data.news()