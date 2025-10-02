#from flask import flask: This imports the main Flask Class to create the Voting System Web Application
#render_template: This function is used to render HTML templates for the web pages.
#request: This module is used to handle incoming request data from the client (like form submissions
#redirect: function is used to redirect users to different routes within the application.
#url_for: This function is used to build URLs for specific functions dynamically.
#flash: This function is used to send one-time messages to users, often used for notifications
from flask import Flask, render_template, request, redirect, url_for, flash

#importing mysql.connector and Error to connect and handle MySQL database operations
import mysql.connector
from mysql.connector import Error 


app = Flask(__name__)
app.secret_key = 'cbu_voting_system'


db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'voting_system_db' 
}


