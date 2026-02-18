from flask import Flask, render_template, request, redirect, session
import mysql.connector
import pandas as pd
import os
from datetime import timedelta

app = Flask(__name__)

# =====================================================
# ✅ SECRET KEY + SESSION SETTINGS
# =====================================================
app.secret_key = "customer_calling_system_2026"
app.permanent_session_lifetime = timedelta(days=7)

# =====================================================
# ✅ UPLOAD FOLDER SETTINGS
# =====================================================
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# =====================================================
# ✅ DATABASE CONNECTION
# =====================================================
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="0000",
    database="customer_calling"
)

cursor = db.cursor(buffered=True)

# =====================================================
# ✅ HOME PAGE
# =====================================================
@app.route("/")
def home():
    return render_template("homepage.html")


# =====================================================
# ✅ LOGIN PAGE (Admin / Manager / Employee)
# =====================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        db.reconnect()

        username = request.form["username"]
        password = request.form["password"]

        # -------- ADMIN LOGIN --------
        cursor.execute(
            "SELECT * FROM admin WHERE username=%s AND password=%s",
            (username, password)
        )
        if cursor.fetchone():
            session["role"] = "admin"
            session["username"] = username
            session.permanent = True
            return redirect("/admin_dashboard")

        # -------- MANAGER LOGIN --------
        cursor.execute(
            "SELECT * FROM managers WHERE username=%s AND password=%s",
            (username, password)
        )
        if cursor.fetchone():
            session["role"] = "manager"
            session["username"] = username
            session.permanent = True
            return redirect("/manager_dashboard")

        # -------- EMPLOYEE LOGIN --------
        cursor.execute(
            "SELECT * FROM employees WHERE username=%s AND password=%s",
            (username, password)
        )
        if cursor.fetchone():
            session["role"] = "employee"
            session["username"] = username
            session.permanent = True
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

    cursor.execute("SELECT * FROM customers")
    customers = cursor.fetchall()

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()

    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()

    return render_template(
        "admin_dashboard.html",
        customers=customers,
        employees=employees,
        teams=teams
    )


# =====================================================
# ✅ ADMIN: ADD EMPLOYEE
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
# ✅ ADMIN: VIEW EMPLOYEES
# =====================================================
@app.route("/employees")
def employees_page():
    if session.get("role") != "admin":
        return redirect("/login")

    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()

    return render_template("employees.html", employees=employees)


# =====================================================
# ✅ ADMIN: ADD CUSTOMER (Manual)
# =====================================================
@app.route("/add_customer", methods=["POST"])
def add_customer():
    if session.get("role") != "admin":
        return redirect("/login")

    cname = request.form["cust_name"]
    cphone = request.form["cust_phone"]
    cemail = request.form["cust_email"]
    cgender = request.form["cust_gender"]
    caddress = request.form["cust_address"]

    cursor.execute("""
        INSERT INTO customers(name, phone, email, gender, address, status)
        VALUES(%s,%s,%s,%s,%s,'Pending')
    """, (cname, cphone, cemail, cgender, caddress))

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
# ✅ ADMIN: DELETE CUSTOMER
# =====================================================
@app.route("/delete_customer/<int:id>")
def delete_customer(id):
    if session.get("role") != "admin":
        return redirect("/login")

    cursor.execute("DELETE FROM customers WHERE id=%s", (id,))
    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
# ✅ ADMIN: EDIT CUSTOMER
# =====================================================
@app.route("/edit_customer/<int:id>", methods=["GET", "POST"])
def edit_customer(id):
    if session.get("role") != "admin":
        return redirect("/login")

    cursor.execute("SELECT * FROM customers WHERE id=%s", (id,))
    customer = cursor.fetchone()

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        email = request.form["email"]
        gender = request.form["gender"]
        address = request.form["address"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE customers
            SET name=%s, phone=%s, email=%s,
                gender=%s, address=%s, status=%s
            WHERE id=%s
        """, (name, phone, email, gender, address, status, id))

        db.commit()
        return redirect("/admin_dashboard")

    return render_template("edit_customer.html", customer=customer)


# =====================================================
# ✅ ADMIN: CLEAR CALL HISTORY
# =====================================================
@app.route("/clear_history", methods=["POST"])
def clear_history():
    if session.get("role") != "admin":
        return redirect("/login")

    cursor.execute("DELETE FROM call_history")
    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
# ✅ TEAM MANAGEMENT (ADMIN)
# =====================================================
@app.route("/create_team", methods=["POST"])
def create_team():
    if session.get("role") != "admin":
        return redirect("/login")

    team_name = request.form["team_name"]

    cursor.execute("INSERT INTO teams(team_name) VALUES(%s)", (team_name,))
    db.commit()

    return redirect("/admin_dashboard")


@app.route("/add_team_member", methods=["POST"])
def add_team_member():
    if session.get("role") != "admin":
        return redirect("/login")

    team_id = request.form["team_id"]
    employee_id = request.form["employee_id"]

    cursor.execute("""
        INSERT INTO team_members(team_id, employee_id)
        VALUES(%s,%s)
    """, (team_id, employee_id))

    db.commit()
    return redirect("/admin_dashboard")


@app.route("/assign_team_customers", methods=["POST"])
def assign_team_customers():
    if session.get("role") != "admin":
        return redirect("/login")

    team_id = request.form["team_id"]
    customer_ids = request.form.getlist("customer_ids")

    for cid in customer_ids:
        cursor.execute(
            "UPDATE customers SET team_id=%s WHERE id=%s",
            (team_id, cid)
        )

    db.commit()
    return redirect("/admin_dashboard")


# =====================================================
# ✅ EMPLOYEE DASHBOARD
# =====================================================
@app.route("/employee")
def employee_page():
    if session.get("role") != "employee":
        return redirect("/login")

    username = session["username"]

    cursor.execute("SELECT id, name FROM employees WHERE username=%s", (username,))
    emp = cursor.fetchone()

    emp_id = emp[0]
    emp_name = emp[1]

    cursor.execute("SELECT * FROM customers WHERE employee_id=%s", (emp_id,))
    customers = cursor.fetchall()

    return render_template(
        "employee.html",
        customers=customers,
        emp_name=emp_name
    )


# =====================================================
# ✅ EMPLOYEE: UPDATE CUSTOMER STATUS
# =====================================================
@app.route("/update_status/<int:id>/<status>")
def update_status(id, status):
    if session.get("role") != "employee":
        return redirect("/login")

    cursor.execute("SELECT name FROM customers WHERE id=%s", (id,))
    cname = cursor.fetchone()[0]

    emp_user = session["username"]

    cursor.execute("UPDATE customers SET status=%s WHERE id=%s", (status, id))

    cursor.execute("""
        INSERT INTO call_history(employee_username, customer_name, status)
        VALUES(%s,%s,%s)
    """, (emp_user, cname, status))

    db.commit()
    return redirect("/employee")


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
