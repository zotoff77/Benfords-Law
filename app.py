from flask import Flask, request, render_template, session, g
from werkzeug.utils import secure_filename
import sqlite3
import os
import csv
import pandas as pd

# Create Flask App instance
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['DATABASE'] = 'file_storage.db'


# Create database and table if they don't exist
def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE
            )
        ''')
        db.commit()


# Get database connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
    return db


# Clear session and close database connection on shutdown
@app.teardown_appcontext
def close_db(error):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# Clear session and remove uploaded file on startup
@app.before_request
def clear_session():
    session.clear()
    session['uploaded_file'] = None


# Populate file list from database
def get_file_list():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT filename FROM files')
    return cursor.fetchall()


# Save uploaded file to database
def save_file_to_db(filename):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO files (filename) VALUES (?)', (filename,))
    db.commit()


@app.route("/", methods=["GET", "POST"])
def upload_file():
    init_db()

    if request.method == "POST":
        file = request.files["file"]
        # Process the uploaded file here

        # Analyze the content of the file to determine the separator
        dialect = csv.Sniffer().sniff(file.read(1024).decode('utf-8'))
        file.seek(0)

        # Read the file into a pandas DataFrame
        df = pd.read_csv(file, dialect=dialect)

        # Save the file to the database
        filename = secure_filename(file.filename)
        save_file_to_db(filename)

        # Get a snippet of the file data
        data = df.head(20) if len(df) > 0 else None
        columns = [data.columns.tolist()] + data.values.tolist()

        return render_template("upload.html", file_list=get_file_list(), data=columns, error_message=None)

    return render_template("upload.html", file_list=get_file_list(), data=None, error_message=None)


@app.route('/process', methods=['POST'])
def process_file():
    selected_file = request.form['selected_file']
    selected_column = request.form['selected_column']

    # Get the file data from the database
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM files WHERE filename = ?', (selected_file,))
    result = cursor.fetchone()
    filename = result[1] if result else None

    if filename:
        # Load the file data into a DataFrame
        df = pd.read_csv(filename)

        # Perform the desired processing on the selected column
        data = df[selected_column]

        # Perform the processing and return the result
        # ... (Add your processing code here)
        return f"Selected file: {filename}, Selected column: {selected_column}"

    return "File not found"


if __name__ == '__main__':
    app.run(debug=True)
