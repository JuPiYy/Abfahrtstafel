"""
Routes and views for the flask application.
"""

from flask import render_template

from Abfahrtstafel import app
from Abfahrtstafel import data

@app.route('/')
def start():
    return data.departures()