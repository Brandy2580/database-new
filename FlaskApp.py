from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import pyodbc
from openpyxl import Workbook
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Update with your secret key

def connect_to_database():
    try:
        connection_string = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=C:\Users\bmunyaradzi.AONZWARSHRE\Desktop\excel for database\combined.accdb;'
        return pyodbc.connect(connection_string)
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/fetch_data', methods=['GET', 'POST'])
def fetch_data():
    table_name = request.form.get('table_name', 'aprilrecords')
    search_term = request.form.get('search_term', '')
    
    connection = connect_to_database()
    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for('home'))

    cursor = connection.cursor()

    # Prepare the query
    query = f"SELECT * FROM [{table_name}] WHERE 1=1"
    params = []
    
    if search_term:
        # Check if the search term is numeric
        if search_term.isdigit():
            query += " AND (certNO = ?)"
            params.append(int(search_term))  # Cast to int if it's a number
        else:
            query += " AND (name LIKE ? OR surname LIKE ?)"
            params.extend([f"%{search_term}%", f"%{search_term}%"])

    cursor.execute(query, params)
    all_results = cursor.fetchall()  # Fetch all results

    # Limit to first 10 records for display
    results = all_results[:10]
    column_names = [column[0] for column in cursor.description]

    cursor.close()
    connection.close()
    return render_template('data_view.html', results=results, column_names=column_names, table_name=table_name, total_records=len(all_results))

@app.route('/search', methods=['POST'])
def search():
    search_term = request.form.get('search_term')
    table_name = request.form.get('table_name', 'aprilrecords')

    connection = connect_to_database()
    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for('home'))

    cursor = connection.cursor()
    query = f"SELECT * FROM [{table_name}] WHERE 1=1"
    params = []
    
    if search_term:
        query += " AND (name LIKE ? OR surname LIKE ? OR certNO = ?)"
        params.extend([f"%{search_term}%", f"%{search_term}%", search_term])

    cursor.execute(query, params)
    results = cursor.fetchall()
    column_names = [column[0] for column in cursor.description]

    cursor.close()
    connection.close()
    return render_template('data_view.html', results=results, column_names=column_names, table_name=table_name)

@app.route('/fetch_verified', methods=['GET'])
def fetch_verified():
    table_name = request.args.get('table_name', 'aprilrecords')  # Default to aprilrecords
    connection = connect_to_database()
    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for('home'))

    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM [{table_name}] WHERE status = 'verified'")
    results = cursor.fetchall()
    column_names = [column[0] for column in cursor.description]

    cursor.close()
    connection.close()
    return render_template('data_view.html', results=results, column_names=column_names, table_name=table_name)

@app.route('/download_verified', methods=['GET'])
def download_verified():
    table_name = request.args.get('table_name', 'aprilrecords')  # Default to aprilrecords
    connection = connect_to_database()
    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for('home'))

    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM [{table_name}] WHERE status = 'verified'")
    results = cursor.fetchall()
    column_names = [column[0] for column in cursor.description]

    # Create an Excel workbook and add a worksheet
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Verified Records"

    # Add column headers
    sheet.append(column_names)

    # Add data rows
    for row in results:
        # Convert pyodbc.Row to a tuple
        sheet.append(tuple(row))

    # Save the workbook to a bytes buffer
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    cursor.close()
    connection.close()

    return send_file(output, as_attachment=True, download_name="verified_records.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route('/toggle_verification/<int:id>/<table_name>', methods=['POST'])
def toggle_verification(id, table_name):
    connection = connect_to_database()
    if connection is None:
        flash("Database connection failed.")
        return redirect(url_for('fetch_data'))

    cursor = connection.cursor()

    # Fetch current status
    cursor.execute(f"SELECT status FROM [{table_name}] WHERE ID = ?", (id,))
    current_status = cursor.fetchone()

    if current_status is None:
        flash("Record not found.")
        cursor.close()
        connection.close()
        return redirect(url_for('fetch_data', table_name=table_name))

    # Determine new status and date
    if current_status[0] == 'verified':
        new_status = 'unverified'
        new_date = None  # Clear date when unverifying
    else:
        new_status = 'verified'
        new_date = datetime.now()  # Set current datetime

    # Update both status and date_verified
    cursor.execute(f"""
        UPDATE [{table_name}] 
        SET status = ?, date_verified = ?
        WHERE ID = ?
    """, (new_status, new_date, id))
    
    connection.commit()

    cursor.close()
    connection.close()
    return redirect(url_for('fetch_data', table_name=table_name))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)