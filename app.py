from flask import Flask, request, render_template, session
import pandas as pd
import os
import csv

# Create Flask App instance
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Clear session on startup
@app.before_request
def clear_session():
    session.clear()

@app.route("/", methods=["GET", "POST"])
def upload_file():

    if request.method == "POST":
        file = request.files["file"]
        # Process the uploaded file here

        # Analyze the content of the file to determine the separator
        dialect = csv.Sniffer().sniff(file.read(1024).decode('utf-8'))
        file.seek(0)

        # Read the file into a pandas DataFrame
        df = pd.read_csv(file, dialect=dialect)

        # Store the DataFrame in the session
        # session['df'] = df.to_dict()

       # Get a snippet of the file data
        data = df.head(20) if len(df) > 0 else None  # Adjust the number of rows as needed
        columns = [data.keys().to_list()] + data.values.tolist()
        return render_template("upload.html", data=columns, error_message=None)

    return render_template("upload.html", data=None, error_message=None)



@app.route('/process', methods=['POST'])
def process_column():
    column = request.form['column']

    # Get the DataFrame from the session
    df = pd.DataFrame(session['df'])

    # Extract the selected column
    data = df[column]

    # Perform the desired processing on the selected column

    return f"Selected column: {column}"

if __name__ == '__main__':
    app.run(debug=True)
