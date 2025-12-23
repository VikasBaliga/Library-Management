from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
DB = "library.db"

def get_db():
    return sqlite3.connect(DB)

def init_db():
    with get_db() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            membership TEXT,
            borrow_limit INTEGER
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY,
            title TEXT,
            author TEXT,
            available_copies INTEGER
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS borrows (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            book_id INTEGER,
            borrowed_at TEXT,
            due_date TEXT,
            returned_at TEXT,
            fine INTEGER
        )
        """)


        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO users VALUES (1, 'Alice', 'BASIC', 2)")
            c.execute("INSERT INTO users VALUES (2, 'Bob', 'PREMIUM', 5)")

            c.execute("INSERT INTO books VALUES (1, 'Book', 'Bob Pines', 3)")
            c.execute("INSERT INTO books VALUES (2, 'Book the sequel', 'Bob Pines 2', 2)")

        conn.commit()



@app.route("/")
def books():
    with get_db() as conn:
        books = conn.execute("SELECT * FROM books").fetchall()
    return render_template("books.html", books=books)

@app.route("/borrow/<int:book_id>")
def borrow(book_id):
    user_id = 1

    with get_db() as conn:
        c = conn.cursor()

        active = c.execute(
            "SELECT COUNT(*) FROM borrows WHERE user_id=? AND returned_at IS NULL",
            (user_id,)
        ).fetchone()[0]

        limit = c.execute(
            "SELECT borrow_limit FROM users WHERE id=?",
            (user_id,)
        ).fetchone()[0]

        if active >= limit:
            return "Borrow limit exceeded"

        copies = c.execute(
            "SELECT available_copies FROM books WHERE id=?",
            (book_id,)
        ).fetchone()[0]

        if copies <= 0:
            return "Book not available"

        due = datetime.now() + timedelta(days=14)

        c.execute("""
        INSERT INTO borrows (user_id, book_id, borrowed_at, due_date, fine)
        VALUES (?, ?, ?, ?, 0)
        """, (user_id, book_id, datetime.now(), due))

        c.execute(
            "UPDATE books SET available_copies = available_copies - 1 WHERE id=?",
            (book_id,)
        )

        conn.commit()

    return redirect(url_for("borrowed"))

@app.route("/borrowed")
def borrowed():
    with get_db() as conn:
        borrows = conn.execute("""
        SELECT b.id, books.title, b.due_date, b.returned_at
        FROM borrows b
        JOIN books ON books.id = b.book_id
        """).fetchall()

    return render_template("borrowed.html", borrows=borrows)

@app.route("/add-book", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        copies = int(request.form["copies"])

        with get_db() as conn:
            conn.execute("""
            INSERT INTO books (title, author, available_copies)
            VALUES (?, ?, ?)
            """, (title, author, copies))
            conn.commit()

        return redirect(url_for("books"))

    return render_template("add_book.html")


@app.route("/return/<int:borrow_id>")
def return_book(borrow_id):
    today = datetime.now()

    with get_db() as conn:
        c = conn.cursor()

        borrow = c.execute("""
        SELECT book_id, due_date FROM borrows WHERE id=?
        """, (borrow_id,)).fetchone()

        due = datetime.fromisoformat(borrow[1])
        fine = 0

        if today > due:
            days_late = (today - due).days
            fine = days_late * 10

        c.execute("""
        UPDATE borrows
        SET returned_at=?, fine=?
        WHERE id=?
        """, (today, fine, borrow_id))

        c.execute("""
        UPDATE books
        SET available_copies = available_copies + 1
        WHERE id=?
        """, (borrow[0],))

        conn.commit()

    return redirect(url_for("borrowed"))

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)

