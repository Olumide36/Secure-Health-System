from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import bcrypt
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = "secret_key"


# -----------------------------
# Create SQLite database
# -----------------------------
def create_db():
    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password BLOB,
        role TEXT
    )
    """)

    conn.commit()
    conn.close()

create_db()


# -----------------------------
# MongoDB connection
# -----------------------------
MONGO_URI = "mongodb+srv://2515057:password2515057@cluster0.bst3nup.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)

db = client["healthcare"]

patients_collection = db["patients"]
appointments_collection =["appointments"]

# -----------------------------
# Home
# -----------------------------
@app.route("/")
def home():
    return render_template("login.html")


# -----------------------------
# Register
# -----------------------------
@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        conn = sqlite3.connect("auth.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username,password,role) VALUES (?,?,?)",
                (username, hashed_password, role)
            )
            conn.commit()

        except:
            return "User already exists"

        finally:
            conn.close()

        return redirect(url_for("home"))

    return render_template("register.html")


# -----------------------------
# Login
# -----------------------------
@app.route("/login", methods=["POST"])
def login():

    username = request.form["username"]
    password = request.form["password"]

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()

    conn.close()

    if user:

        stored_password = user[2]

        if bcrypt.checkpw(password.encode("utf-8"), stored_password):

            session["user"] = user[1]
            session["role"] = user[3]

            return redirect(url_for("dashboard"))

    return "Invalid login"


# -----------------------------
# Dashboard
# -----------------------------
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():

    if "user" not in session:
        return redirect(url_for("home"))

    search = request.form.get("search")

    if session["role"] == "patient":

        patients = list(
            patients_collection.find({"owner": session["user"]})
        )

    else:

        if search:
            patients = list(
                patients_collection.find(
                    {"name": {"$regex": search, "$options": "i"}}
                )
            )
        else:
            patients = list(patients_collection.find())

    return render_template(
        "dashboard.html",
        user=session["user"],
        role=session["role"],
        patients=patients
    )


# -----------------------------
# View patient record
# -----------------------------
@app.route("/view_record")
def view_record():

    if "user" not in session:
        return redirect(url_for("home"))

    if session["role"] != "patient":
        return "Access Forbidden"

    patients = list(
        patients_collection.find({"owner": session["user"]})
    )

    return render_template("view_record.html", patients=patients)


# -----------------------------
# Add patient
# -----------------------------
@app.route("/add_patient", methods=["GET","POST"])
def add_patient():

    if "user" not in session:
        return redirect(url_for("home"))

    if session["role"] not in ["clinician","admin"]:
        return "Access Forbidden"

    conn = sqlite3.connect("auth.db")
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM users WHERE role='patient'")
    patients = cursor.fetchall()

    if request.method == "POST":

        patient = {
            "owner": request.form.get("owner"),
            "name": request.form.get("name"),
            "age": request.form.get("age"),
            "blood_pressure": request.form.get("blood_pressure"),
            "cholesterol": request.form.get("cholesterol"),
            "fasting_blood_sugar": request.form.get("fasting_blood_sugar"),
            "resting_ecg": request.form.get("resting_ecg"),
            "exercise_angina": request.form.get("exercise_angina")

             }

        patients_collection.insert_one(patient)

        conn.close()

        return redirect(url_for("dashboard"))

    conn.close()

    return render_template("add_patient.html", patients=patients)


# -----------------------------
# Book appointment
# -----------------------------
@app.route("/book_appointment", methods=["GET","POST"])
def book_appointment():

    if "user" not in session:
        return redirect(url_for("home"))

    if session["role"] != "patient":
        return "Access Forbidden"

    if request.method == "POST":

        appointment = {
            "patient": session["user"],
            "date": request.form.get("date"),
            "time": request.form.get("time"),
            "reason": request.form.get("reason"),
            "status": "Pending"
        }

        appointments_collection.insert_one(appointment)

        return redirect(url_for("my_appointments"))

    return render_template("book_appointment.html")


# --------------------------------
# Patient view their appointment
# --------------------------------
@app.route("/my_appointments")
def my_appointments():

    if session["role"] != "patient":
        return "Access Forbidden"

    appointments = list(
        appointments_collection.find({"patient": session["user"]})
    )

    return render_template("my_appointments.html", appointments=appointments)


# -----------------------------
# Add/clinician view all
# -----------------------------
@app.route("/appointments")
def appointments():

    if session["role"] not in ["admin","clinician"]:
        return "Access Forbidden"

    appointments = list(appointments_collection.find())

    return render_template("appointments.html", appointments=appointments)


# -----------------------------
# Edit patient
# -----------------------------
@app.route("/update_appointment/<id>/<status>")
def update_appointment(id, status):

    appointments_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"status": status}}
    )

    return redirect(url_for("appointments"))


# -----------------------------
# Edit patient
# -----------------------------
@app.route("/edit_patient/<id>", methods=["GET","POST"])
def edit_patient(id):

    if session["role"] not in ["clinician","admin"]:
        return "Access Forbidden"

    patient = patients_collection.find_one({"_id": ObjectId(id)})

    if request.method == "POST":

        patients_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set":{
                "name": request.form.get("name"),
                "age": request.form.get("age"),
                "blood_pressure": request.form.get("blood_pressure"),
                "cholesterol": request.form.get("cholesterol"),
                "fasting_blood_sugar": request.form.get("fasting_blood_sugar"),
                "resting_ecg": request.form.get("resting_ecg"),
                "exercise_angina": request.form.get("exercise_angina")
            }}
        )

        return redirect(url_for("dashboard"))

    return render_template("edit_patient.html", patient=patient)


# -----------------------------
# Delete patient
# -----------------------------
@app.route("/delete_patient/<id>")
def delete_patient(id):

    if session["role"] not in ["clinician","admin"]:
        return "Access Forbidden"

    patients_collection.delete_one({"_id": ObjectId(id)})

    return redirect(url_for("dashboard"))


# -----------------------------
# Logout
# -----------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# -----------------------------
# Run Flask
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)