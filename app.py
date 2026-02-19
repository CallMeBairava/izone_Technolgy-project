from flask import Flask, render_template, request, redirect, session, send_file
import mysql.connector
import pandas as pd
import os
from datetime import timedelta
from fpdf import FPDF
from itertools import cycle

app = Flask(__name__)

# =====================================================
# ✅ SECRET KEY + SESSION TIMEOUT
# =====================================================
app.secret_key = "customer_calling_system_2026"
app.permanent_session_lifetime = timedelta(minutes=30)

# =====================================================
# ✅ UPLOAD FOLDER
# =====================================================
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# =====================================================
# ✅ DATABASE CONNECTION
# =====================================================
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="0000",
        database="customer_calling"
    )

# =====================================================
# ✅ HOME PAGE
# =====================================================
@app.route("/")
def home():
    return render_template("homepage.html")

# =====================================================
# ✅ LOGIN PAGE (ADMIN / MANAGER / EMPLOYEE)
# =====================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor(buffered=True)

        # ✅ ADMIN LOGIN → MANAGER DASHBOARD
        cursor.execute("SELECT * FROM admin WHERE username=%s AND password=%s",
                       (username, password))
        if cursor.fetchone():
            session.permanent = True
            session["role"] = "admin"
            session["username"] = username
            return redirect("/manager_dashboard")

        # ✅ MANAGER LOGIN → CEO DASHBOARD
        cursor.execute("SELECT * FROM managers WHERE username=%s AND password=%s",
                       (username, password))
        if cursor.fetchone():
            session.permanent = True
            session["role"] = "manager"
            session["username"] = username
            return redirect("/ceo_dashboard")

        # ✅ EMPLOYEE LOGIN
        cursor.execute("SELECT * FROM employees WHERE username=%s AND password=%s",
                       (username, password))
        if cursor.fetchone():
            session.permanent = True
            session["role"] = "employee"
            session["username"] = username
            return redirect("/employee")

        return "❌ Invalid Username or Password"

    return render_template("login.html")

# =====================================================
# ✅ MANAGER DASHBOARD (OLD ADMIN PANEL)
# =====================================================
@app.route("/manager_dashboard")
def manager_dashboard():
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM customers")
    customers = cursor.fetchall()

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()

    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()

    db.close()

    return render_template(
        "manager_dashboard.html",
        customers=customers,
        employees=employees,
        teams=teams
    )

# =====================================================
# ✅ CEO DASHBOARD (OLD MANAGER REPORT PANEL)
# =====================================================
@app.route("/ceo_dashboard")
def ceo_dashboard():
    if session.get("role") != "manager":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    # Summary Counts
    cursor.execute("SELECT COUNT(*) FROM customers")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers WHERE status='Willing'")
    willing = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers WHERE status='Not Willing'")
    not_willing = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    # Teams + Employees
    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()

    # Call History
    cursor.execute("""
        SELECT id, employee_username, customer_id, status, call_time, notes
        FROM call_history
        ORDER BY call_time DESC
    """)
    history = cursor.fetchall()

    db.close()

    return render_template(
        "ceo_dashboard.html",
        total=total,
        willing=willing,
        not_willing=not_willing,
        pending=pending,
        teams=teams,
        employees=employees,
        history=history
    )

# =====================================================
# ✅ EMPLOYEES PAGE
# =====================================================
@app.route("/employees")
def employees_page():
    if session.get("role") not in ["admin", "manager"]:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()

    db.close()

    return render_template("employees.html", employees=employees)

# =====================================================
# ✅ ADD EMPLOYEE
# =====================================================
@app.route("/add_employee", methods=["POST"])
def add_employee():
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO employees(name, phone, username, password)
        VALUES(%s,%s,%s,%s)
    """, (
        request.form["name"],
        request.form["phone"],
        request.form["username"],
        request.form["password"]
    ))

    db.commit()
    db.close()

    return redirect("/manager_dashboard")

# =====================================================
# ✅ ADD CUSTOMER
# =====================================================
@app.route("/add_customer", methods=["POST"])
def add_customer():
    if session.get("role") != "admin":
        return redirect("/login")

    priority = request.form.get("cust_priority", "Medium")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO customers(name, phone, email, gender, address, status, priority)
        VALUES(%s,%s,%s,%s,%s,'Pending',%s)
    """, (
        request.form["cust_name"],
        request.form["cust_phone"],
        request.form["cust_email"],
        request.form["cust_gender"],
        request.form["cust_address"],
        priority
    ))

    db.commit()
    db.close()

    return redirect("/manager_dashboard")

# =====================================================
# ✅ EXCEL UPLOAD (NORMAL)
# =====================================================
@app.route("/upload_customers", methods=["POST"])
def upload_customers():
    if session.get("role") != "admin":
        return redirect("/login")

    file = request.files["file"]
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    df = pd.read_excel(filepath)

    db = get_db()
    cursor = db.cursor()

    for _, row in df.iterrows():
        priority = row.get("priority", "Medium")

        cursor.execute("""
            INSERT INTO customers(name, phone, email, gender, address, status, priority)
            VALUES(%s,%s,%s,%s,%s,'Pending',%s)
        """, (
            row["name"],
            row["phone"],
            row["email"],
            row["gender"],
            row["address"],
            priority
        ))

    db.commit()
    db.close()

    return redirect("/manager_dashboard")

# =====================================================
# ✅ EXCEL UPLOAD AUTO ASSIGN
# =====================================================
@app.route("/upload_customers_auto", methods=["POST"])
def upload_customers_auto():
    if session.get("role") != "admin":
        return redirect("/login")

    file = request.files["file"]
    team_id = request.form["team_id"]

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    df = pd.read_excel(filepath)

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM employees WHERE team_id=%s", (team_id,))
    employees = cursor.fetchall()

    if not employees:
        return "❌ No employees found in this team."

    employee_cycle = cycle(employees)

    for _, row in df.iterrows():
        emp_id = next(employee_cycle)[0]
        priority = row.get("priority", "Medium")

        cursor.execute("""
            INSERT INTO customers
            (name, phone, email, gender, address, status, team_id, assigned_to, priority)
            VALUES(%s,%s,%s,%s,%s,'Pending',%s,%s,%s)
        """, (
            row["name"],
            row["phone"],
            row["email"],
            row["gender"],
            row["address"],
            team_id,
            emp_id,
            priority
        ))

    db.commit()
    db.close()

    return redirect("/manager_dashboard")

# =====================================================
# ✅ CREATE TEAM
# =====================================================
@app.route("/create_team", methods=["POST"])
def create_team():
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("INSERT INTO teams(team_name) VALUES(%s)",
                   (request.form["team_name"],))

    db.commit()
    db.close()

    return redirect("/manager_dashboard")

# =====================================================
# ✅ ASSIGN EMPLOYEE TO TEAM
# =====================================================
@app.route("/add_team_member", methods=["POST"])
def add_team_member():
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE employees
        SET team_id=%s
        WHERE id=%s
    """, (request.form["team_id"], request.form["employee_id"]))

    db.commit()
    db.close()

    return redirect("/manager_dashboard")

# =====================================================
# ✅ REASSIGN CUSTOMER (ADMIN + MANAGER)
# =====================================================
@app.route("/reassign_customer", methods=["POST"])
def reassign_customer():
    if session.get("role") not in ["admin", "manager"]:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE customers
        SET team_id=%s
        WHERE id=%s
    """, (request.form["team_id"], request.form["customer_id"]))

    db.commit()
    db.close()

    if session["role"] == "admin":
        return redirect("/manager_dashboard")
    else:
        return redirect("/ceo_dashboard")

# =====================================================
# ✅ EMPLOYEE PANEL
# =====================================================
@app.route("/employee")
def employee_page():
    if session.get("role") != "employee":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    emp_username = session["username"]

    cursor.execute("SELECT id,name FROM employees WHERE username=%s",
                   (emp_username,))
    emp = cursor.fetchone()

    emp_id = emp[0]

    cursor.execute("SELECT * FROM customers WHERE assigned_to=%s", (emp_id,))
    customers = cursor.fetchall()

    db.close()

    return render_template("employee.html",
                           customers=customers,
                           employee=emp)

# =====================================================
# ✅ SAVE CALL NOTE
# =====================================================
@app.route("/save_call_note", methods=["POST"])
def save_call_note():
    if session.get("role") != "employee":
        return redirect("/login")

    customer_id = request.form["customer_id"]
    status = request.form["status"]
    notes = request.form["notes"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE customers
        SET status=%s, completed_time=NOW()
        WHERE id=%s
    """, (status, customer_id))

    cursor.execute("""
        INSERT INTO call_history(employee_username, customer_id, status, call_time, notes)
        VALUES(%s,%s,%s,NOW(),%s)
    """, (session["username"], customer_id, status, notes))

    db.commit()
    db.close()

    return redirect("/employee")

# =====================================================
# ✅ EXPORT EXCEL REPORT (CEO)
# =====================================================
@app.route("/export_excel")
def export_excel():
    if session.get("role") != "manager":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM call_history")
    data = cursor.fetchall()
    db.close()

    df = pd.DataFrame(data,
                      columns=["ID", "Employee", "CustomerID", "Status", "Time", "Notes"])

    file_name = "call_report.xlsx"
    df.to_excel(file_name, index=False)

    return send_file(file_name, as_attachment=True)

# =====================================================
# ✅ EXPORT PDF REPORT (CEO)
# =====================================================
@app.route("/export_pdf")
def export_pdf():
    if session.get("role") != "manager":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM call_history")
    data = cursor.fetchall()
    db.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)

    pdf.cell(200, 10, txt="Customer Calling Report", ln=True, align="C")
    pdf.ln(10)

    for row in data:
        line = f"{row[1]} | CustomerID: {row[2]} | {row[3]} | Notes: {row[5]}"
        pdf.multi_cell(0, 8, line)

    file_name = "call_report.pdf"
    pdf.output(file_name)

    return send_file(file_name, as_attachment=True)

# =====================================================
# ✅ LOGOUT
# =====================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# =====================================================
# ✅ RUN SERVER
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)
