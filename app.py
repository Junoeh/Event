from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import mysql.connector
import os
from dotenv import load_dotenv
from waitress import serve
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = "Bruh"

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

def get_db():
    db = mysql.connector.connect(
        host=os.getenv("host"),
        user=os.getenv("user"),
        password=os.getenv("password"),
        database="eventsite"
    )
    return db


@app.route("/waitress")
def waitress():
    return "Waitress is working!"

@app.route("/")
def home():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT events.id, events.title, events.event_date, events.location, users.email
        FROM events
        JOIN users ON events.user_id = users.id
        ORDER BY events.event_date
    """)
    events = cursor.fetchall()

    cursor.close()

    return render_template("index.html", events=events)


@app.route("/event/new", methods=["GET", "POST"])
def new_event():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        event_date = request.form["event_date"]
        location = request.form["location"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO events (title, event_date, location, user_id)
            VALUES (%s, %s, %s, %s)
        """, (title, event_date, location, session["user_id"]))

        db.commit()
        cursor.close()

        return redirect("/")

    now = datetime.now().strftime('%Y-%m-%dT%H:%M')
    return render_template("new_event.html", now=now)


@app.route("/join/<event_id>")
def join_event(event_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT IGNORE INTO signups (user_id, event_id)
        VALUES (%s, %s)
    """, (session["user_id"], event_id))

    db.commit()
    cursor.close()

    return redirect("/")


@app.route("/delete/<event_id>")
def delete_event(event_id):
    if "user_id" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT is_admin FROM users WHERE id = %s",
        (session["user_id"],)
    )
    user = cursor.fetchone()

    if user and user[0] == 1:
        cursor.execute("DELETE FROM signups WHERE event_id = %s", (event_id,))
        cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
        db.commit()

    cursor.close()

    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO users (email, password_hash)
            VALUES (%s, %s)
        """, (email, hashed_password))

        db.commit()
        cursor.close()
        db.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            SELECT id, password_hash, is_admin FROM users WHERE email = %s
        """, (email,))
        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["is_admin"] = bool(user[2])
            return redirect("/")
        return render_template("login.html", error="Wrong email orpassword")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
    

@app.route("/faq")
def faq():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT faq_sporsmal.sporsmal, faq_sporsmal.opprettet, users.email
        FROM faq_sporsmal
        JOIN users ON faq_sporsmal.user_id = users.id
        ORDER BY faq_sporsmal.opprettet DESC
    """)
    user_questions = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("faq.html", user_questions=user_questions)


@app.route("/faq/ask", methods=["GET", "POST"])
def ask_question():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        sporsmal = request.form["sporsmal"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO faq_sporsmal (user_id, sporsmal)
            VALUES (%s, %s)
        """, (session["user_id"], sporsmal))

        db.commit()
        cursor.close()
        db.close()

        return redirect("/faq")

    return render_template("ask_question.html")


@app.route("/faq/delete-data", methods=["GET", "POST"])
def delete_faq_data():
    if request.method == "POST":
        email = request.form["email"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            DELETE faq_sporsmal
            FROM faq_sporsmal
            JOIN users ON faq_sporsmal.user_id = users.id
            WHERE users.email = %s
        """, (email,))

        db.commit()
        cursor.close()
        db.close()

        return "All FAQ questions connected to this email have been deleted."

    return render_template("delete_data.html")


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5000)