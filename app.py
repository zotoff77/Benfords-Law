from flask import Flask, request, render_template, session, g
from werkzeug.utils import secure_filename
import sqlite3
import os
import csv
import pandas as pd
from io import StringIO
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.offline as py
import numpy as np


# Create Flask App instance
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['DATABASE'] = 'datasets.db'


# Create database and table if they don't exist
def init_db():
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



@app.route("/", methods=["GET", "POST"])
def upload_file():
    init_db()

    # Process selected file, if any
    selected_file = request.form.get('selected_file')
    data = None

    if selected_file:
        # Get the file content from the database
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT *  FROM files WHERE filename = ?", (selected_file,))
        result = cursor.fetchone()
        if result:
            content = result[2]
            dialect = csv.Sniffer().sniff(content, delimiters=result[3])
            # Parse content into list of lists  
            data = list(csv.reader(StringIO(content), dialect=dialect))[:10]
        return render_template("upload.html", file_list=get_file_list(), selected_file=selected_file, data=data, error_message=None)


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
            cursor.execute("INSERT INTO files (filename, content, delimiter) VALUES (?, ?, ?)", (file.filename, content, dialect.delimiter))
            db.commit()
        else:
            error_message = "Invalid file format. Only comma or tab-separated files are allowed."
            return render_template("upload.html", file_list=get_file_list(), selected_file=None, error_message=error_message)
        

    return render_template("upload.html", file_list=get_file_list(), data=None, error_message=None)


@app.route('/process', methods=['POST'])
def process_file():
    try:
        selected_file = request.form['selected_file']
        selected_column = request.form['selected_column']

        # Get the file data from the database
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM files WHERE filename = ?', (selected_file,))
        result = cursor.fetchone()

        if not result:
            return render_template("results.html", error_message="File not found in the database.")

        content = result[2]
        dialect = csv.Sniffer().sniff(content, delimiters=result[3])
        # Parse content into list of lists  
        data = list(csv.reader(StringIO(content), dialect=dialect))

        if not data or selected_column not in data[0]:
            return render_template("results.html", error_message="Invalid data or column not found.")
        
        col_index = data[0].index(selected_column)
        col_data = [row[col_index] for row in data[1:]]
        
            
        # Calculate Benford's Distribution & our data distribution
        benford_distr = [np.log10(1 + 1/d) for d in range(1, 10)]
        
        # Extract the leading digit from each number, skip for 'None', '' empty str and zeros
        leading_digits = [int(str(abs(float(num)))[0]) for num in col_data if num and float(num) != 0.0]
        
        frequency = pd.value_counts(leading_digits, normalize=True).sort_index()

        # Create the bar traces
        trace_benford = go.Bar(x=list(range(1, 10)), y=benford_distr, name='Benford')
        trace_data = go.Bar(x=frequency.index, y=frequency.values, name='Data')

        # Create the layout
        layout = go.Layout(
            title='Benford vs Data Distribution',
            xaxis=dict(title='Leading Digit'),
            yaxis=dict(title='Frequency'),
            barmode='group'
        )

        # Create the figure and convert to HTML
        fig = go.Figure(data=[trace_benford, trace_data], layout=layout)
        plot_html = py.plot(fig, output_type='div', include_plotlyjs=False)
        
        return render_template("results.html", file_list=None, selected_file=selected_file, data=col_data, plot=plot_html, error_message=None)
    
    except Exception as e:
        return render_template("results.html", data=[], error_message="Server error: " + str(e))      
    



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
