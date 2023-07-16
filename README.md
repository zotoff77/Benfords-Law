# Challenge: Benford's Law
---

### How to run?:
**Download and run my image from docker repository:**
- docker pull zotoff77/l7:latest
- docker run -p 8080:5000 zotoff77/l7:latest
- in browser: localhost:8080

#### Source code files are provided in the email (.zip) and also available via github repository:
https://github.com/zotoff77/Benfords-Law.git

### Description:
This project is a web application built on the Flask framework in Python, incorporating the Benford's Law concept to analyze user-uploaded data files.
It utilizes a SQLite database for storing and managing the uploaded files. The CSV module is used to parse user files, and pandas is employed to process the data and generate frequency distributions.
The project uses Plotly for visualizing the distribution of leading digits in the data compared against the Benford's distribution.

The application adopts the MVC (Model-View-Controller) pattern; the model corresponds to the interactions with the SQLite database, views are handled via Flask's render_template function aided by Jinja2 templating for dynamic HTML generation, and the controller is represented by route functions in the Flask app. Context management pattern is applied for efficient handling of database connections.

---
### Assignments & Status:
**[DONE]** Create a web application (Python, Node or other back-end is fine if needed) that:
**[DONE]** 1) can ingest the attached example file (census_2009b) and any other flat file with a viable target column. Note that other columns in user-submitted files may or may not be the same as the census data file and users are known for submitting files that don't always conform to rigid expectations. How you deal with files that don't conform to the expectations of the application is up to you, but should be reasonable and defensible.

**[DONE]** 2) validates Benford’s assertion based on the '7_2009' column in the supplied file

**[DONE]** 3) Outputs back to the user a graph of the observed distribution of numbers with an overlay of the expected distribution of numbers. The output should also inform the user of whether the observed data matches the expected data distribution.

**[DONE]** The delivered package should contain a docker file that allows us to docker run the application and test the functionality directly.

**[DONE]** Stretch challenge: persist the uploaded information to a database so a user can come to the application and browse through datasets uploaded by other users. No user authentication/user management is required here… assume anonymous users and public datasets.

**[PASS]** Bonus points for automated tests.

### Submission package:
Source Files (also provided link to git repository)
- app.py
- upload.html
- results.html
- styles.css

This README.md document
