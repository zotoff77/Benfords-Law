from flask import Flask, request, render_template, g
import sqlite3
import csv
import os

# Create Flask App instance
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['DATABASE'] = 'datasets.db'

# Database initialization

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
    return db

def close_db(e=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
    cursor = db.cursor()

    # Create the files table if it doesn't exist
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            content TEXT NOT NULL
        )
        """
    )
    db.commit()

@app.route("/", methods=["GET", "POST"])
def upload_file():
    init_db()

    if request.method == "POST":
        file = request.files["file"]

        # Validate the file format (comma or tab separated)
        allowed_delimiters = [",", "\t"]
        content = file.read().decode("utf-8")
        dialect = csv.Sniffer().sniff(content, delimiters=allowed_delimiters)
        if dialect.delimiter in allowed_delimiters:
            # Save the file and its content to the database
            db = get_db()
            cursor = db.cursor()
            cursor.execute("INSERT INTO files (name, content) VALUES (?, ?)", (file.filename, content))
            db.commit()
        else:
            error_message = "Invalid file format. Only comma or tab-separated files are allowed."
            return render_template("upload.html", file_list=get_file_list(), selected_file=None, error_message=error_message)

    selected_file_name = request.form.get("selected_file")
    if selected_file_name:
        selected_file = get_file(selected_file_name)
    else:
        selected_file = None

    return render_template("upload.html", file_list=get_file_list(), selected_file=selected_file, error_message=None)

def get_file_list():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT name FROM files")
    return cursor.fetchall()

def get_file(file_name):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT content FROM files WHERE name = ?", (file_name,))
    file_content = cursor.fetchone()
    if file_content:
        content = csv.reader(file_content[0].splitlines(), delimiter=',')
        return list(content)
    else:
        return None


if __name__ == '__main__':
    app.run(debug=True)
