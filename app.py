import os

import sqlite3
import pandas as pd
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from io import StringIO
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

# configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# establish connection to sqlite database
db = 'main.db'
conn = sqlite3.connect(db, check_same_thread=False)
cursor = conn.cursor()

conn.close


@app.route("/", methods=["GET", "POST"])
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
                       {"username": request.form.get("username"),
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


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    # if user adds a list, add to database
    if request.method == "POST":
        # make sure file exists and get file name
        if "file" not in request.files or request.files["file"].filename == "":
            flash("No file selected")
            return render_template("upload.html")
        file = request.files["file"]
        name = os.path.splitext(file.filename)[0]
        
        # read file content into a string and pass into pandas
        stream = StringIO(file.stream.read().decode("utf-8"))
        df = pd.read_csv(stream)

        # query database if list with same name exists
        cursor.execute("SELECT * FROM word_lists WHERE name = ?", [name])
        rows = cursor.fetchall()
        if len(rows) != 0:
            flash("List already in database")
        # insert word list name into word_lists table
        else:
            # get word_list id
            cursor.execute("INSERT INTO word_lists (name) VALUES (:name)", [name])
            cursor.execute("SELECT id FROM word_lists WHERE name = :name", [name])
            word_list_id = cursor.fetchall()[0][0]

            # add only new words into database
            cursor.execute("SELECT itl_word FROM words")
            itl_words = cursor.fetchall()
            for value in df.values:
                if value[0] not in itl_words:
                    # insert values into words table
                    cursor.execute("""
                                INSERT INTO words (itl_word, eng_word, itl_sen, eng_sen) SELECT :itl_word, :eng_word, :itl_sen, :eng_sen WHERE NOT EXISTS (
                                SELECT 1 FROM words WHERE itl_word = :itl_word AND eng_word = :eng_word AND itl_sen = :itl_sen AND eng_sen = eng_sen)
                                """, {"itl_word": value[0], "eng_word": value[1], "itl_sen": value[2], "eng_sen": value[3]})
                    # insert id's into word_list_words table
                    cursor.execute("SELECT id FROM words WHERE itl_word = :itl_word", [value[0]])
                    word_id = cursor.fetchall()[0][0]
                    cursor.execute("INSERT INTO word_list_words (word_list_id, word_id) VALUES (:word_list_id, :word_id)",
                               {"word_list_id": word_list_id, "word_id": word_id})
                
            conn.commit()

    return render_template("upload.html")



if __name__ == "__main__":
    app.run(debug=True)