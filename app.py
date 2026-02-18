from flask import Flask, render_template, request, redirect, session, send_file
import mysql.connector
import pandas as pd
import os
from datetime import timedelta
from fpdf import FPDF

app = Flask(__name__)

# =====================================================
# ✅ SECRET KEY + SESSION TIMEOUT (5 MINUTES)
# =====================================================
app.secret_key = "customer_calling_system_2026"
app.permanent_session_lifetime = timedelta(minutes=5)

# =====================================================
#                  UPLOAD FOLDER
# =====================================================
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# =====================================================
#               DATABASE CONNECTION
# =====================================================
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="0000",
    database="customer_calling"
)

cursor = db.cursor(buffered=True)

# =====================================================
#                     HOME PAGE
# =====================================================
@app.route("/")
def home():
    return render_template("homepage.html")


# =====================================================
#                     LOGIN PAGE
# =====================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        db.reconnect()

        username = request.form["username"]
        password = request.form["password"]

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
#                 ADMIN DASHBOARD
# =====================================================
@app.route("/admin_dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect("/login")

    db.reconnect()

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
#                 ADMIN: ADD EMPLOYEE
# =====================================================
@app.route("/add_employee", methods=["POST"])
def add_employee():
    if session.get("role") != "admin":
        return redirect("/login")

    name = request.form["name"]
    phone = request.form["phone"]
    username = request.form["username"]
    password = request.form["password"]

    cursor.execute("""
        INSERT INTO employees(name, phone, username, password)
        VALUES(%s,%s,%s,%s)
    """, (name, phone, username, password))

    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
#                 ADMIN: ADD CUSTOMER MANUALLY
# =====================================================
@app.route("/add_customer", methods=["POST"])
def add_customer():
    if session.get("role") != "admin":
        return redirect("/login")

    name = request.form["cust_name"]
    phone = request.form["cust_phone"]
    email = request.form["cust_email"]
    gender = request.form["cust_gender"]
    address = request.form["cust_address"]

    cursor.execute("""
        INSERT INTO customers(name, phone, email, gender, address, status)
        VALUES(%s,%s,%s,%s,%s,'Pending')
    """, (name, phone, email, gender, address))

    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
#                 ADMIN: UPLOAD CUSTOMERS EXCEL
# =====================================================
@app.route("/upload_customers", methods=["POST"])
def upload_customers():
    if session.get("role") != "admin":
        return redirect("/login")

    file = request.files["file"]
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    df = pd.read_excel(filepath)

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO customers(name, phone, email, gender, address, status)
            VALUES(%s,%s,%s,%s,%s,'Pending')
        """, (row["name"], row["phone"], row["email"],
              row["gender"], row["address"]))

    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
#                 TEAM MANAGEMENT (ADMIN)
# =====================================================
@app.route("/create_team", methods=["POST"])
def create_team():
    team_name = request.form["team_name"]

    cursor.execute("INSERT INTO teams(team_name) VALUES(%s)", (team_name,))
    db.commit()
    return redirect("/admin_dashboard")


@app.route("/add_team_member", methods=["POST"])
def add_team_member():
    team_id = request.form["team_id"]
    employee_id = request.form["employee_id"]

    cursor.execute("""
        UPDATE employees SET team_id=%s WHERE id=%s
    """, (team_id, employee_id))

    db.commit()
    return redirect("/admin_dashboard")


@app.route("/assign_team_customers", methods=["POST"])
def assign_team_customers():
    team_id = request.form["team_id"]
    customer_ids = request.form.getlist("customer_ids")

    for cid in customer_ids:
        cursor.execute("""
            UPDATE customers SET team_id=%s WHERE id=%s
        """, (team_id, cid))

    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
#                 EMPLOYEE DASHBOARD
# =====================================================
@app.route("/employee")
def employee_page():
    if session.get("role") != "employee":
        return redirect("/login")

    emp_username = session["username"]

    cursor.execute("SELECT id, name, team_id FROM employees WHERE username=%s",
                   (emp_username,))
    emp = cursor.fetchone()

    emp_name = emp[1]
    team_id = emp[2]

    cursor.execute("SELECT team_name FROM teams WHERE id=%s", (team_id,))
    team = cursor.fetchone()
    team_name = team[0] if team else "Not Assigned"

    cursor.execute("SELECT * FROM customers WHERE team_id=%s", (team_id,))
    customers = cursor.fetchall()

    return render_template("employee.html",
                           customers=customers,
                           emp_name=emp_name,
                           team_name=team_name)


# =====================================================
#        EMPLOYEE: SAVE STATUS + NOTES AFTER CALL
# =====================================================
@app.route("/save_call_note", methods=["POST"])
def save_call_note():
    if session.get("role") != "employee":
        return redirect("/login")

    customer_id = request.form["customer_id"]
    status = request.form["status"]
    notes = request.form["notes"]

    emp_user = session["username"]

    cursor.execute("""
        UPDATE customers SET status=%s WHERE id=%s
    """, (status, customer_id))

    cursor.execute("SELECT name FROM customers WHERE id=%s", (customer_id,))
    cname = cursor.fetchone()[0]

    cursor.execute("""
        INSERT INTO call_history(employee_username, customer_name, status, notes)
        VALUES(%s,%s,%s,%s)
    """, (emp_user, cname, status, notes))

    db.commit()
    return redirect("/employee")


# =====================================================
#                 MANAGER DASHBOARD
# =====================================================
@app.route("/manager_dashboard")
def manager_dashboard():
    if session.get("role") != "manager":
        return redirect("/login")

    cursor.execute("SELECT COUNT(*) FROM customers")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers WHERE status='Willing'")
    willing = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers WHERE status='Not Willing'")
    not_willing = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM customers WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    # ✅ Teams + Employees List
    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()

    # Call History
    cursor.execute("SELECT * FROM call_history ORDER BY call_time DESC")
    history = cursor.fetchall()

    return render_template(
        "manager_dashboard.html",
        total=total,
        willing=willing,
        not_willing=not_willing,
        pending=pending,
        history=history,
        teams=teams,
        employees=employees
    )


# =====================================================
#                 EXPORT REPORTS
# =====================================================
@app.route("/export_excel")
def export_excel():
    cursor.execute("SELECT * FROM call_history")
    data = cursor.fetchall()

    df = pd.DataFrame(data,
                      columns=["ID", "Employee", "Customer",
                               "Status", "Notes", "Time"])

    file_name = "call_report.xlsx"
    df.to_excel(file_name, index=False)

    return send_file(file_name, as_attachment=True)


@app.route("/export_pdf")
def export_pdf():
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
#                 CLEAR CALL HISTORY (ADMIN)
# =====================================================
@app.route("/clear_history", methods=["POST"])
def clear_history():
    if session.get("role") != "admin":
        return redirect("/login")

    cursor.execute("DELETE FROM call_history")
    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
#                     LOGOUT
# =====================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# =====================================================
#                     RUN SERVER
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)
