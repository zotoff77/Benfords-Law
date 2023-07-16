from flask import Flask, request, redirect, render_template, session, g
import sqlite3
import csv
import pandas as pd
from io import StringIO
import plotly.graph_objects as go
import plotly.offline as py
import numpy as np
import os

def get_db():
    """
    Return database connection
    """
    if (db := getattr(g, '_database', None)) is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
    return db

def init_db():
    """
    Create database and table if they do not exist already
    """
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                delimiter TEXT NOT NULL
            )
        """)
        db.commit()


# Initialize Flask App
app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY=os.urandom(24),
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    DATABASE='datasets.db'
)

# Initialize Database
with app.app_context():
    init_db()


@app.teardown_appcontext
def close_db(error):
    """
    Close the database connection on shutdown
    """
    if (db := getattr(g, '_database', None)) is not None:
        db.close()


@app.before_request
def clear_session():
    """
    Clear session and remove uploaded file on startup
    """
    session.clear()
    session['uploaded_file'] = None


def get_file_list():
    """
    Return a list of all filenames from the database
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT filename FROM files')
    return cursor.fetchall()


@app.route("/", methods=["GET", "POST"])
def main_handle():
    """
    Main page route, handles GET to display the main page and POST to process the file upload
    """
    if request.method == "GET":
        selected_file = request.form.get('selected_file')
        data = None

        if selected_file:
            data = fetch_file_from_db(selected_file)[:10]

            if data:
                return render_template("upload.html", file_list=get_file_list(), selected_file=selected_file, data=data)

        return render_template("upload.html", file_list=get_file_list(), data=None)
    
    elif request.method == "POST":
        if 'btn_upload' in request.form:
            # Upload selected file to the database
            file = request.files["file_to_upload"]
            if not file:
                return render_template("upload.html", file_list=get_file_list(), selected_file=None, error_message="No file selected for upload.")
            
            allowed_delimiters = [",", "\t"]
            content = file.read().decode("utf-8")

            try:
                dialect = csv.Sniffer().sniff(content, delimiters=allowed_delimiters)
            except csv.Error:
                return render_template("upload.html", file_list=get_file_list(), selected_file=None, error_message="Invalid file format. Only comma or tab-separated files are allowed.")

            db = get_db()
            cursor = db.cursor()
            cursor.execute("INSERT INTO files (filename, content, delimiter) VALUES (?, ?, ?)", (file.filename, content, dialect.delimiter))
                        
            db.commit()
        elif 'btn_preview' in request.form:
            # Check if file name was selected from the uploaded files list and show a snippet
            if 'selected_file' not in request.form:
                return render_template("upload.html", file_list=get_file_list(), selected_file=None, error_message="No file selected to preview.")        
            file_name=request.form.get('selected_file')
            data = fetch_file_from_db(file_name)[:10]
            if not data:
                return render_template("upload.html", file_list=get_file_list(), selected_file=None, error_message="No data available.")   
            return render_template("upload.html", file_list=get_file_list(), selected_file = file_name, data=data)
        elif 'btn_process' in request.form:
            selected_file = request.form['selected_file']
            if not selected_file:
                return render_template("upload.html", file_list=get_file_list(), selected_file=None, error_message="Please select a file to process.")   
            
            selected_column = request.form['selected_column']
            if not selected_column:
                return render_template("upload.html", file_list=get_file_list(), selected_file=selected_file, error_message="Please select a column to process.")

            data = fetch_file_from_db(selected_file)

            col_index = data[0].index(selected_column)
            try:
                col_data = [row[col_index] for row in data[1:] if len(row) > col_index]
            except IndexError as e:
                return render_template("upload.html", file_list=get_file_list(), selected_file=selected_file, error_message= str(e))
            

            if data is None or col_data is None:
                return render_template("upload.html", file_list=get_file_list(), selected_file=selected_file, error_message="Invalid data or data not found.")
            try:
                plot_html = calculate_benford_and_generate_plot(col_data)
            except ValueError as e:
                return render_template("upload.html", file_list=get_file_list(), selected_file=selected_file, error_message="Invalid data.")
                
            return render_template("results.html", file_list=None, plot=plot_html)  
    
    return render_template("upload.html", file_list=get_file_list(), data=None)
    


def fetch_file_from_db(filename):
    """
    Fetch the selected file from the database 
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM files WHERE filename = ?", (filename,))
    result = cursor.fetchone()

    if result:
        content = result[2]
        dialect = csv.Sniffer().sniff(content, delimiters=result[3])
        data = list(csv.reader(StringIO(content), dialect=dialect))
        return data

    return None
    



def calculate_benford_and_generate_plot(col_data):
    """
    Calculate Benford's distribution, generate the plot and return the HTML
    """
    benford_distr = [np.log10(1 + 1/d) for d in range(1, 10)]
    leading_digits = [int(str(abs(float(num)))[0]) for num in col_data if num and float(num) != 0.0]
    frequency = pd.value_counts(leading_digits, normalize=True).sort_index()

    trace_benford = go.Bar(x=list(range(1, 10)), y=benford_distr, name="Benford's")
    trace_data = go.Bar(x=frequency.index, y=frequency.values, name='Data from file')

    layout = go.Layout(
        title="Benford's Distribution vs File Data Distribution",
        xaxis=dict(title='Leading Digit'),
        yaxis=dict(title='Frequency'),
        barmode='group'
    )

    fig = go.Figure(data=[trace_benford, trace_data], layout=layout)
    plot_html = py.plot(fig, output_type='div', include_plotlyjs=False)

    return plot_html


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
