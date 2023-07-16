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
    DATABASE='datasets.db' # db path/name
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


def get_file_list():
    """
    Return a list of all filenames from the database
    """
    db = get_db()
    cursor = db.cursor()


def render_error(selected_file=None, error_message='Error!'):
    """
    Render error
    """
    return render_template("upload.html", 
                           file_list=get_file_list(), 
                           selected_file=selected_file, 
                           error_message=error_message)

@app.route("/", methods=["GET", "POST"])
def main_handle():
    """
    Main page route, handles GET to display the main page (default) and POST to upload and process files
    """
    
    data=None
    data_snippet = None
    # we will only accept flat, i.e. comma or tab separated files
    allowed_delimiters = [",", "\t"]
    selected_file = request.form.get('selected_file')
    
    # fetch a snippet of a selected file
    if selected_file:
            data_snippet = fetch_file_from_db(selected_file)[:10]
            
    selected_column = request.form.get('selected_column')
    
    # process incoming POST requests
    if request.method == "POST":
        # Process 'Upload' button press - upload file to the database
        if 'btn_upload' in request.form:
            # Extrace file name from the request
            file = request.files["file_to_upload"]
            if not file:
                return render_error(selected_file=None, error_message="No file selected for upload.")

            # read and parse
            content = file.read().decode("utf-8")

            try:
                dialect = csv.Sniffer().sniff(content, delimiters=allowed_delimiters)
            except csv.Error:
                return render_error(error_message="Invalid file format. Only comma or tab-separated files are allowed.")
            
            # store file in the database for future use
            db = get_db()
            cursor = db.cursor()
            cursor.execute("INSERT INTO files (filename, content, delimiter) VALUES (?, ?, ?)", (file.filename, content, dialect.delimiter))
                        
            db.commit()
        # Process 'Preview File' button press - show a snippet of the file for preview    
        elif 'btn_preview' in request.form:
            # Check if file name was selected from the uploaded files list and load a snippet
            if not selected_file:
                return render_error(error_message="No file selected to preview.")        
            
            file_name=request.form.get('selected_file')
            data_snippet = fetch_file_from_db(file_name)[:10]
            if not data_snippet:
                return render_error(error_message="No data available.")   
            
        # Process 'Process' button press - fetch file content from db and show distribution graphs
        elif 'btn_process' in request.form:
   
            if not selected_file:
                return render_error(selected_file=selected_file, error_message="Please select a file to process.")   
            
            if not selected_column:
                return render_error(selected_file=selected_file, error_message="Please select a column to process.")

            # fetch all file data then only take data for the selected column
            data = fetch_file_from_db(selected_file)

            col_index = data[0].index(selected_column)
            try:
                col_data = [row[col_index] for row in data[1:] if len(row) > col_index]
            except IndexError as e:
                return render_error(selected_file=selected_file, error_message= str(e))
            
            if data is None or col_data is None:
                return render_error(selected_file=selected_file, error_message="Invalid data or data not found.")
            
            # calculate benford's and file data's chart data, create plot html and render it
            try:
                plot_html = calculate_benford_and_generate_plot(col_data)
            except ValueError as e:
                return render_error(selected_file=selected_file, error_message="Invalid data.")
                
            # note template is different 'results.html'
            return render_template("results.html", file_list=None, plot=plot_html)  
    
    # default render - shall cover all GET and some POST scenarios
    return render_template("upload.html", file_list=get_file_list(), selected_file=selected_file, data=data_snippet)
    


def fetch_file_from_db(filename):
    """
    returns selected file data from the database, based on provided filename or None
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
    Calculate Benford's distribution, generate the plot with 2 sets of data and return the HTML
    """
    benford_distr = [np.log10(1 + 1/d) for d in range(1, 10)]
    
    # extract leading zeros from provided list and calculate frequency
    leading_digits = [int(str(abs(float(num)))[0]) for num in col_data if num and float(num) != 0.0]
    frequency = pd.value_counts(leading_digits, normalize=True).sort_index()

    # Build the plot
    trace_benford = go.Bar(x=list(range(1, 10)), y=benford_distr, name="Benford's")
    trace_data = go.Bar(x=frequency.index, y=frequency.values, name='Data from file')

    layout = go.Layout(
        title="Benford's Distribution vs File Data Distribution",
        xaxis=dict(title='Leading Digit'),
        yaxis=dict(title='Frequency'),
        barmode='group'
    )
    
    fig = go.Figure(data=[trace_benford, trace_data], layout=layout)
    
    # generate html for the plot
    plot_html = py.plot(fig, output_type='div', include_plotlyjs=False)

    return plot_html


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
