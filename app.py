from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "goodbye-sein-secret-key"

ADMIN_PASSWORD = "sein1234"

def init_db():
    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            edit_password TEXT NOT NULL,
            message TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/letter")
def letter():
    return render_template("letter.html")

@app.route("/info")
def info():
    return render_template("info.html")

@app.route("/write")
def write():
    student_id = request.args.get("student_id")
    name = request.args.get("name")
    edit_password = request.args.get("edit_password")

    if not student_id or not name or not edit_password:
        return redirect("/info")

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()
    cursor.execute("SELECT message, edit_password FROM messages WHERE student_id = ?", (student_id,))
    existing = cursor.fetchone()
    conn.close()

    if existing:
        old_message, saved_password = existing

        if edit_password != saved_password:
            return "수정 비밀번호가 맞지 않아요. 뒤로 가서 다시 입력해주세요."

        return render_template("write.html", student_id=student_id, name=name, edit_password=edit_password, message=old_message, mode="edit")

    return render_template("write.html", student_id=student_id, name=name, edit_password=edit_password, message="", mode="new")

@app.route("/submit", methods=["POST"])
def submit():
    student_id = request.form.get("student_id")
    name = request.form.get("name")
    edit_password = request.form.get("edit_password")
    message = request.form.get("message")

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM messages WHERE student_id = ?", (student_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE messages
            SET name = ?, edit_password = ?, message = ?
            WHERE student_id = ?
        """, (name, edit_password, message, student_id))
    else:
        cursor.execute("""
            INSERT INTO messages (student_id, name, edit_password, message)
            VALUES (?, ?, ?, ?)
        """, (student_id, name, edit_password, message))

    conn.commit()
    conn.close()

    return redirect("/complete")

@app.route("/complete")
def complete():
    return render_template("complete.html")

@app.route("/board")
def board():
    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT student_id, name
        FROM messages
        ORDER BY student_id ASC
    """)
    students = cursor.fetchall()
    conn.close()

    return render_template("board.html", students=students)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    error = None

    if request.method == "POST":
        password = request.form.get("password")

        if password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/admin")
        else:
            error = "비밀번호가 맞지 않아요."

    if session.get("admin"):
        conn = sqlite3.connect("messages.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, student_id, name, message
            FROM messages
            ORDER BY student_id ASC
        """)
        messages = cursor.fetchall()
        conn.close()

        return render_template("admin.html", messages=messages, login=True)

    return render_template("admin.html", login=False, error=error)

@app.route("/delete/<int:message_id>", methods=["POST"])
def delete_message(message_id):
    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/admin")

init_db()

if __name__ == "__main__":
    app.run(debug=True)