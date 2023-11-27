# main_routes.py
# now you can import the products module
from app.data.products import products
from app.data.image_urls import image_urls
from app.data.events import image_urls
from flask import render_template
from . import main


@main.route('/')
def index():
    return render_template('main/index.html')


@main.route('/board-of-directors')
def boardofdirectors():
    return render_template('main/board-of-directors.html')


@main.route('/projects')
def projects():
    return render_template('projects.html')


@main.route('/adopt-new-yorks-past')
def new_yorks_past():
    return render_template('main/adopt_new_yorks_past.html', products=products, image_urls=image_urls)


@main.route('/events')
def events():
    return render_template('main/events.html', image_urls=image_urls)


@main.route('/contact')
def contact():
    return render_template('main/contact.html')


@main.route('/koch-congressional-project')
def koch_congressional_project():
    return render_template('main/koch_congressional_project.html')


@main.route('/about')
def about():
    return render_template('main/about.html')


@main.app_errorhandler(404)
def http_error_handler(error):
    return render_template("error/404NotFound.html"), 404
