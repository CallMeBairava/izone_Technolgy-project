from flask import Flask, render_template, request, redirect, session, send_file
import mysql.connector
import pandas as pd
import os
from datetime import timedelta
from fpdf import FPDF

app = Flask(__name__)

# =====================================================
# ✅ SECRET KEY + SESSION TIMEOUT (30 MINUTES)
# =====================================================
app.secret_key = "customer_calling_system_2026"
app.permanent_session_lifetime = timedelta(minutes=30)

# =====================================================
# ✅ UPLOAD FOLDER
# =====================================================
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists("uploads"):
    os.makedirs("uploads")


# =====================================================
# ✅ DATABASE CONNECTION FUNCTION
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
# ✅ LOGIN PAGE
# =====================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor(buffered=True)

        # -------- ADMIN LOGIN --------
        cursor.execute("SELECT * FROM admin WHERE username=%s AND password=%s",
                       (username, password))
        if cursor.fetchone():
            session.permanent = True
            session["role"] = "admin"
            session["username"] = username
            return redirect("/admin_dashboard")

        # -------- MANAGER LOGIN --------
        cursor.execute("SELECT * FROM managers WHERE username=%s AND password=%s",
                       (username, password))
        if cursor.fetchone():
            session.permanent = True
            session["role"] = "manager"
            session["username"] = username
            return redirect("/manager_dashboard")

        # -------- EMPLOYEE LOGIN --------
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
# ✅ ADMIN DASHBOARD
# =====================================================
@app.route("/admin_dashboard")
def admin_dashboard():
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

    return render_template("admin_dashboard.html",
                           customers=customers,
                           employees=employees,
                           teams=teams)


# =====================================================
# ✅ ADMIN: ADD EMPLOYEE
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
    return redirect("/admin_dashboard")


# =====================================================
# ✅ ADMIN: ADD CUSTOMER MANUALLY
# =====================================================
@app.route("/add_customer", methods=["POST"])
def add_customer():
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO customers(name, phone, email, gender, address, status)
        VALUES(%s,%s,%s,%s,%s,'Pending')
    """, (
        request.form["cust_name"],
        request.form["cust_phone"],
        request.form["cust_email"],
        request.form["cust_gender"],
        request.form["cust_address"]
    ))

    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
# ✅ ADMIN: UPLOAD CUSTOMERS USING EXCEL
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
        cursor.execute("""
            INSERT INTO customers(name, phone, email, gender, address, status)
            VALUES(%s,%s,%s,%s,%s,'Pending')
        """, (
            row["name"],
            row["phone"],
            row["email"],
            row["gender"],
            row["address"]
        ))

    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
# ✅ ADMIN: CREATE TEAM
# =====================================================
@app.route("/create_team", methods=["POST"])
def create_team():
    if session.get("role") != "admin":
        return redirect("/login")

    team_name = request.form["team_name"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute("INSERT INTO teams(team_name) VALUES(%s)", (team_name,))
    db.commit()

    return redirect("/admin_dashboard")


# =====================================================
# ✅ ADMIN: ASSIGN EMPLOYEE TO TEAM
# =====================================================
@app.route("/add_team_member", methods=["POST"])
def add_team_member():
    if session.get("role") != "admin":
        return redirect("/login")

    team_id = request.form["team_id"]
    employee_id = request.form["employee_id"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE employees
        SET team_id=%s
        WHERE id=%s
    """, (team_id, employee_id))

    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
# ✅ ADMIN: ASSIGN CUSTOMERS TO TEAM
# =====================================================
@app.route("/assign_team_customers", methods=["POST"])
def assign_team_customers():
    if session.get("role") != "admin":
        return redirect("/login")

    team_id = request.form["team_id"]
    customer_ids = request.form.getlist("customer_ids")

    db = get_db()
    cursor = db.cursor()

    for cid in customer_ids:
        cursor.execute("""
            UPDATE customers
            SET team_id=%s
            WHERE id=%s
        """, (team_id, cid))

    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
# ✅ EMPLOYEES LIST PAGE
# =====================================================
@app.route("/employees")
def employees_page():
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()

    return render_template("employees.html", employees=employees)


# =====================================================
# ✅ EDIT EMPLOYEE
# =====================================================
@app.route("/edit_employee/<int:id>", methods=["GET", "POST"])
def edit_employee(id):
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        cursor.execute("""
            UPDATE employees
            SET name=%s, phone=%s, username=%s, password=%s
            WHERE id=%s
        """, (
            request.form["name"],
            request.form["phone"],
            request.form["username"],
            request.form["password"],
            id
        ))
        db.commit()
        return redirect("/employees")

    cursor.execute("SELECT * FROM employees WHERE id=%s", (id,))
    emp = cursor.fetchone()

    return render_template("edit_employee.html", emp=emp)


# =====================================================
# ✅ EDIT CUSTOMER
# =====================================================
@app.route("/edit_customer/<int:id>", methods=["GET", "POST"])
def edit_customer(id):
    if session.get("role") != "admin":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        cursor.execute("""
            UPDATE customers
            SET name=%s, phone=%s, status=%s
            WHERE id=%s
        """, (
            request.form["name"],
            request.form["phone"],
            request.form["status"],
            id
        ))
        db.commit()
        return redirect("/admin_dashboard")

    cursor.execute("SELECT * FROM customers WHERE id=%s", (id,))
    customer = cursor.fetchone()

    return render_template("edit_customer.html", customer=customer)


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

    cursor.execute("SELECT id, name, team_id FROM employees WHERE username=%s",
                   (emp_username,))
    emp = cursor.fetchone()

    if emp is None:
        return "❌ Employee not found in database"

    team_id = emp[2]

    cursor.execute("SELECT * FROM customers WHERE team_id=%s", (team_id,))
    customers = cursor.fetchall()

    return render_template("employee.html", customers=customers)


# =====================================================
# ✅ SAVE CALL NOTE + STATUS UPDATE
# =====================================================
@app.route("/save_call_note", methods=["POST"])
def save_call_note():
    if session.get("role") != "employee":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    customer_id = request.form["customer_id"]
    status = request.form["status"]
    notes = request.form["notes"]

    emp_user = session["username"]

    cursor.execute("UPDATE customers SET status=%s WHERE id=%s",
                   (status, customer_id))

    cursor.execute("SELECT name FROM customers WHERE id=%s", (customer_id,))
    cname = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO call_history(employee_username, customer_name, status, notes)
        VALUES(%s,%s,%s,%s)
    """, (emp_user, cname, status, notes))

    db.commit()
    return redirect("/employee")


# =====================================================
# ✅ MANAGER DASHBOARD
# =====================================================
@app.route("/manager_dashboard")
def manager_dashboard():
    if session.get("role") != "manager":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT COUNT(*) FROM customers")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers WHERE status='Willing'")
    willing = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers WHERE status='Not Willing'")
    not_willing = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()

    cursor.execute("SELECT * FROM call_history ORDER BY call_time DESC")
    history = cursor.fetchall()

    return render_template("manager_dashboard.html",
                           total=total,
                           willing=willing,
                           not_willing=not_willing,
                           pending=pending,
                           teams=teams,
                           employees=employees,
                           history=history)


# =====================================================
# ✅ EXPORT REPORTS (MANAGER)
# =====================================================
@app.route("/export_excel")
def export_excel():
    if session.get("role") != "manager":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM call_history")
    data = cursor.fetchall()

    df = pd.DataFrame(
        data,
        columns=["ID", "Employee", "Customer", "Status", "Notes", "Time"]
    )

    file_name = "call_report.xlsx"
    df.to_excel(file_name, index=False)

    return send_file(file_name, as_attachment=True)


@app.route("/export_pdf")
def export_pdf():
    if session.get("role") != "manager":
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM call_history")
    data = cursor.fetchall()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)

    pdf.cell(200, 10, txt="Customer Calling Report", ln=True, align="C")
    pdf.ln(8)

    for row in data:
        line = f"{row[1]} | {row[2]} | {row[3]} | Notes: {row[4]}"
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
