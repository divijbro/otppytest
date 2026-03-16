import psycopg2
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import resend
import datetime
from random import randint

auth_email = "cooldivijdhingra@gmail.com"

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.environ.get("DB_URL")
resend.api_key = os.environ.get("RESEND_API_KEY")


@app.route("/")
def home():
    return "Backend Running 🚀"


@app.route("/sendotp", methods=["POST"])
def send_otp():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"success": False, "error": "Email required"}), 400

    otp = str(randint(100000, 999999))
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO otps (email, otp, expires_at)
            VALUES (%s, %s, %s)
        """, (email, otp, expiry))

        conn.commit()
        cursor.close()
        conn.close()

        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [email],
            "subject": "Your MNMK OTP Code 🔐",
            "html": f"""
                <h2>Your OTP Code</h2>
                <p>Your OTP is: <strong>{otp}</strong></p>
                <p>This code expires in 5 minutes.</p>
            """
        })

        return jsonify({"success": True})

    except Exception as e:
        print("OTP Error:", e)
        return jsonify({"success": False}), 500


@app.route("/verifyotp", methods=["POST"])
def verify_otp():
    data = request.json
    email = data.get("email")
    otp_input = data.get("otp")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT otp, expires_at
            FROM otps
            WHERE email=%s
            ORDER BY expires_at DESC
            LIMIT 1
        """, (email,))

        record = cursor.fetchone()

        cursor.close()
        conn.close()

        if not record:
            return jsonify({"success": False})

        otp_db, expiry = record

        print("DB OTP:", otp_db)
        print("USER OTP:", otp_input)
        print("EXPIRY:", expiry)
        print("NOW:", datetime.datetime.utcnow())

        if str(otp_db).strip() == str(otp_input).strip() and expiry > datetime.datetime.utcnow():
            return jsonify({"success": True})
        else:
            return jsonify({"success": False})

    except Exception as e:
        print("Verify Error:", e)
        return jsonify({"success": False}), 500


@app.route("/createbooking", methods=["POST"])
def create_booking():
    data = request.json

    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    date = data.get("date")
    venue = data.get("venue")
    time = data.get("time")

    booking_id = f"MNMK-{int(datetime.datetime.utcnow().timestamp())}"

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO bookings (booking_id, name, email, phone, event_date, venue, time, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (booking_id, name, email, phone, date, venue, time, "pending"))

        conn.commit()
        cursor.close()
        conn.close()

        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [email],
            "subject": "Booking Confirmed 🎉",
            "html": f"""
                <h2>🎉 Booking Confirmed!</h2>
                <p>Your Booking ID: <strong>{booking_id}</strong></p>
                <p>We will contact you shortly.</p>
            """
        })

        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": [auth_email],
            "subject": f"🎉 New Booking Request – {booking_id}",
            "html": f"""
                <div style="font-family: Arial, sans-serif; padding:20px;">
                    <h2 style="color:#ff4081;">🎉 New Booking Request Received</h2>
                    
                    <p><strong>Booking ID:</strong> {booking_id}</p>
                    <hr>

                    <h3>Customer Details</h3>
                    <p><strong>Name:</strong> {name}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Phone:</strong> {phone}</p>
                    <p><strong>Date:</strong> {date}</p>
                    <p><strong>Venue:</strong> {venue}</p>
                    <p><strong>Time:</strong> {time}</p>
                    

                    <hr>

                    <p style="color:#666;">
                        Please contact the customer within 24 hours.
                    </p>

                    <p>
                        – MNMK Celebrations System 🚀
                    </p>
                </div>
            """
        })

        return jsonify({
            "success": True,
            "booking_id": booking_id
        })

    except Exception as e:
        print("Booking Error:", e)
        return jsonify({"success": False}), 500

@app.route("/checkavailability", methods=["POST"])
def check_availability():
    data = request.json
    date = data.get("date")
    venue = data.get("venue")
    time = data.get("time")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM bookings
            WHERE event_date = %s
            AND venue = %s
            AND time = %s
            AND status = 'pending'
        """, (date, venue, time))

        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        if count > 0:
            return jsonify({"available": False})
        else:
            return jsonify({"available": True})

    except Exception as e:
        print("Availability Error:", e)
        return jsonify({"available": False}), 500
    
@app.route("/admin_check", methods = ["POST"])
def changestatus():
    data = request.json
    status = "confirmed"
    booking_id = data.get("booking_id")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE bookings
            SET status = %s
            WHERE booking_id = %s
        """, (status, booking_id))

        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"success": True})
    except Exception as e:
        print("Update Error:", e)
        return jsonify({"success": False}), 500
    
@app.route("/admin/bookings", methods=["GET"])
def get_bookings():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT booking_id, name, email, phone, event_date, venue, time, status
            FROM bookings
            ORDER BY event_date DESC
        """)

        rows = cursor.fetchall()

        bookings = []
        for r in rows:
            bookings.append({
                "booking_id": r[0],
                "name": r[1],
                "email": r[2],
                "phone": r[3],
                "date": r[4],
                "venue": r[5],
                "time": r[6],
                "status": r[7]
            })

        cursor.close()
        conn.close()

        return jsonify(bookings)

    except Exception as e:
        print("Admin Error:", e)
        return jsonify({"error": "Failed"}), 500
    
if __name__ == "__main__":
    app.run(debug=True)
