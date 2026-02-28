import psycopg2
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import resend
import datetime
from random import randint

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

        if otp_db == otp_input and expiry > datetime.datetime.utcnow():
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
    message = data.get("message")

    booking_id = f"MNMK-{int(datetime.datetime.utcnow().timestamp())}"

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO bookings (booking_id, name, email, phone, message, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (booking_id, name, email, phone, message, "false"))

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

        return jsonify({
            "success": True,
            "booking_id": booking_id
        })

    except Exception as e:
        print("Booking Error:", e)
        return jsonify({"success": False}), 500


if __name__ == "__main__":
    app.run(debug=True)
