from flask import Flask, render_template, request, redirect, session, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "goodbye-sein-secret-key"

ADMIN_PASSWORD = "sein1234"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


def init_db():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            edit_password TEXT NOT NULL,
            message TEXT NOT NULL,
            photo TEXT
        )
    """)
    conn.commit()
    conn.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()
    cursor.execute("SELECT message, edit_password FROM messages WHERE student_id = ?", (student_id,))
    existing = cursor.fetchone()
    conn.close()

    if existing:
        old_message, saved_password = existing

        if edit_password != saved_password:
            return "수정 비밀번호가 맞지 않아요. 뒤로 가서 다시 입력해주세요."

        return render_template(
            "write.html",
            student_id=student_id,
            name=name,
            edit_password=edit_password,
            message=old_message,
            mode="edit"
        )

    return render_template(
        "write.html",
        student_id=student_id,
        name=name,
        edit_password=edit_password,
        message="",
        mode="new"
    )


@app.route("/submit", methods=["POST"])
def submit():
    student_id = request.form.get("student_id")
    name = request.form.get("name")
    edit_password = request.form.get("edit_password")
    message = request.form.get("message")

    photo = request.files.get("photos")
    photo_filename = None

    if photo and photo.filename != "":
        if allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_filename = f"{student_id}_{filename}"
            photo_path = os.path.join(app.config["UPLOAD_FOLDER"], photo_filename)
            photo.save(photo_path)

    conn = sqlite3.connect("messages.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, photo FROM messages WHERE student_id = ?", (student_id,))
    existing = cursor.fetchone()

    if existing:
        old_photo = existing[1]

        if photo_filename is None:
            photo_filename = old_photo

        cursor.execute("""
            UPDATE messages
            SET name = ?, edit_password = ?, message = ?, photo = ?
            WHERE student_id = ?
        """, (name, edit_password, message, photo_filename, student_id))
    else:
        cursor.execute("""
            INSERT INTO messages (student_id, name, edit_password, message, photo)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, name, edit_password, message, photo_filename))

    conn.commit()
    conn.close()

    return redirect("/complete")


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


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
            SELECT id, student_id, name, message, photo
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


if __name__ == "__main__":
    init_db()
    app.run(debug=True)