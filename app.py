import os

import sqlite3
import pandas as pd
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

# configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# load csv file into pandas dataframe
# TODO: turn into function
csv_filepath = '10-words.csv'
df = pd.read_csv(csv_filepath)

# establish connection to sqlite database
db = 'main.db'
conn = sqlite3.connect(db, check_same_thread=False)
cursor = conn.cursor()

# write dataframe to sqlite table
words = 'words'
df.to_sql(words, conn, if_exists='replace', index=False)

conn.close


@app.route("/")
@login_required
def index():
    # get username
    cursor.execute("SELECT username FROM users WHERE id = :id", [session["user_id"]])
    username = cursor.fetchall()[0][0]
    return render_template("index.html", username=username)


# register user
@app.route("/register", methods=["GET", "POST"])
def register():
    # clear previous session
    session.clear()

    if request.method == "POST":
        # check credentials
        if not request.form.get("username"):
            flash("Must provide username")
            return render_template("register.html")
        elif not request.form.get("password"):
            flash("Must provide password")
            return render_template("register.html")
        elif not request.form.get("confirmation"):
            flash("Must confirm password")
            return render_template("register.html")
        elif request.form.get("password") != request.form.get("confirmation"):
            flash("Passwords must match")
            return render_template("register.html")
        
        # check database for username
        cursor.execute("SELECT * FROM users WHERE username = :username", [request.form.get("username")])
        rows = cursor.fetchall()
        if len(rows) != 0:
            flash("Username already exists")
            return render_template("register.html")

        # register new user
        cursor.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", 
                       { "username": request.form.get("username"),
                       "hash" : generate_password_hash(request.form.get("password"))})
        conn.commit()

        # search database for new user
        cursor.execute("SELECT * FROM users WHERE username = :username", [request.form.get("username")])
        rows = cursor.fetchall()

        # create new session for the new user
        session["user_id"] = rows[0][0]
        
        # redirect to homepage    
        return redirect(url_for("index"))
    
    else:
        return render_template("register.html")


# log user in
@app.route("/login", methods=["GET", "POST"])
def login():
    # clear user_id
    session.clear()

    if request.method == "POST":
        # ensure username was submitted
        if not request.form.get("username"):
            flash("Must enter username")
            return render_template("login.html")
        # ensure password was submitted
        elif not request.form.get("password"):
            flash("Must enter password")
            return render_template("login.html")

        # query database for username
        cursor.execute("SELECT * FROM users WHERE username = ?",
                              [request.form.get("username")])
        rows = cursor.fetchall()

        # ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return redirect(url_for("login"))
        
        # remember which user has logged in
        session["user_id"] = rows[0][0]

        # redirect user to home page
        return redirect(url_for("index"))
    
    # user reached route via GET (by clicking a link or redirect)
    else:
        return render_template("login.html")
    

@app.route("/logout")
def logout():
    # clear user_id
    session.clear()

    # redirect user to home page
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)