from flask import Flask, render_template, request, redirect, session
import mysql.connector
import os
from dotenv import load_dotenv
from waitress import serve

load_dotenv()

app = Flask(__name__)
app.secret_key = "Bruh"

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

    return render_template("new_event.html")


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


if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5000)