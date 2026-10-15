from flask import Flask, render_template, jsonify, request
import sqlite3
from pathlib import Path
from uuid import uuid4

app = Flask(__name__)
DATABASE = Path(__file__).with_name("booking.db")


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                seat_number TEXT NOT NULL,
                booking_status TEXT NOT NULL DEFAULT 'CONFIRMED',
                payment_status TEXT NOT NULL DEFAULT 'SUCCESS',
                refund_status TEXT NOT NULL DEFAULT 'NOT_REQUESTED',
                UNIQUE(event_name, seat_number)
            )
        """)


@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/api/db-status")
def db_status():
    try:
        with get_db() as connection:
            connection.execute("SELECT 1")

        return jsonify({
            "success": True,
            "database": "SQLite",
            "message": "Database connected successfully!"
        })
    except sqlite3.Error as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


@app.route("/api/bookings", methods=["GET"])
def get_bookings():
    search = request.args.get("search", "").strip()

    with get_db() as connection:
        rows = connection.execute("""
            SELECT * FROM bookings
            WHERE event_name LIKE ?
            ORDER BY id DESC
        """, (f"%{search}%",)).fetchall()

    return jsonify({
        "success": True,
        "bookings": [dict(row) for row in rows]
    })


@app.route("/api/bookings", methods=["POST"])
def create_booking():
    data = request.get_json(silent=True) or {}

    event_name = str(data.get("event_name", "")).strip()
    seat_number = str(data.get("seat_number", "")).strip()

    if not event_name or not seat_number:
        return jsonify({
            "success": False,
            "message": "Event name and seat number are required."
        }), 400

    try:
        with get_db() as connection:
            cursor = connection.execute("""
                INSERT INTO bookings (event_name, seat_number)
                VALUES (?, ?)
            """, (event_name, seat_number))

            booking_id = cursor.lastrowid

        return jsonify({
            "success": True,
            "booking_id": booking_id,
            "event_name": event_name,
            "seat_number": seat_number,
            "message": "Booking saved successfully!"
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "success": False,
            "message": "This seat is already booked for this event!"
        }), 409

    except sqlite3.Error as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


def run_database_test(test_name):
    # Ovvoru test-kum separate event name.
    # Test mudindha piragu test data delete aagum.
    event = "TEST-" + uuid4().hex[:12]
    result = "FAIL"
    message = "Test failed."

    try:
        with get_db() as connection:

            if test_name == "Search Results":
                connection.execute("""
                    INSERT INTO bookings (event_name, seat_number)
                    VALUES (?, ?)
                """, (event, "A1"))

                rows = connection.execute("""
                    SELECT * FROM bookings WHERE event_name = ?
                """, (event,)).fetchall()

                passed = (
                    len(rows) == 1
                    and rows[0]["seat_number"] == "A1"
                )
                message = (
                    "Search returned the expected booking."
                    if passed else "Search result was incorrect."
                )

            elif test_name == "Seat Allocation":
                connection.execute("""
                    INSERT INTO bookings (event_name, seat_number)
                    VALUES (?, ?)
                """, (event, "A1"))

                connection.execute("""
                    INSERT INTO bookings (event_name, seat_number)
                    VALUES (?, ?)
                """, (event, "A2"))

                rows = connection.execute("""
                    SELECT seat_number FROM bookings
                    WHERE event_name = ?
                """, (event,)).fetchall()

                seats = {row["seat_number"] for row in rows}
                passed = seats == {"A1", "A2"}
                message = (
                    "Two different seats were allocated correctly."
                    if passed else "Seat allocation was incorrect."
                )

            elif test_name == "Duplicate Booking":
                connection.execute("""
                    INSERT INTO bookings (event_name, seat_number)
                    VALUES (?, ?)
                """, (event, "A1"))

                try:
                    connection.execute("""
                        INSERT INTO bookings (event_name, seat_number)
                        VALUES (?, ?)
                    """, (event, "A1"))
                    passed = False
                    message = "Duplicate booking was allowed."
                except sqlite3.IntegrityError:
                    passed = True
                    message = "Duplicate booking was correctly rejected."

            elif test_name == "Payment Failure":
                connection.execute("""
                    INSERT INTO bookings
                        (event_name, seat_number, payment_status)
                    VALUES (?, ?, ?)
                """, (event, "A1", "FAILED"))

                row = connection.execute("""
                    SELECT payment_status FROM bookings
                    WHERE event_name = ? AND seat_number = ?
                """, (event, "A1")).fetchone()

                passed = row["payment_status"] == "FAILED"
                message = (
                    "Failed payment status was saved correctly."
                    if passed else "Failed payment status was incorrect."
                )

            elif test_name == "Cancellation":
                connection.execute("""
                    INSERT INTO bookings (event_name, seat_number)
                    VALUES (?, ?)
                """, (event, "A1"))

                connection.execute("""
                    UPDATE bookings
                    SET booking_status = 'CANCELLED'
                    WHERE event_name = ? AND seat_number = ?
                """, (event, "A1"))

                row = connection.execute("""
                    SELECT booking_status FROM bookings
                    WHERE event_name = ? AND seat_number = ?
                """, (event, "A1")).fetchone()

                passed = row["booking_status"] == "CANCELLED"
                message = (
                    "Booking cancellation was saved correctly."
                    if passed else "Booking cancellation failed."
                )

            elif test_name == "Refund":
                connection.execute("""
                    INSERT INTO bookings
                        (event_name, seat_number, booking_status,
                         payment_status, refund_status)
                    VALUES (?, ?, ?, ?, ?)
                """, (event, "A1", "CANCELLED", "SUCCESS", "NOT_REQUESTED"))

                connection.execute("""
                    UPDATE bookings
                    SET refund_status = 'REFUNDED'
                    WHERE event_name = ? AND seat_number = ?
                """, (event, "A1"))

                row = connection.execute("""
                    SELECT refund_status FROM bookings
                    WHERE event_name = ? AND seat_number = ?
                """, (event, "A1")).fetchone()

                passed = row["refund_status"] == "REFUNDED"
                message = (
                    "Refund status was updated correctly."
                    if passed else "Refund status update failed."
                )

            elif test_name == "Booking Status":
                connection.execute("""
                    INSERT INTO bookings
                        (event_name, seat_number, booking_status, payment_status)
                    VALUES (?, ?, ?, ?)
                """, (event, "A1", "CONFIRMED", "SUCCESS"))

                connection.execute("""
                    INSERT INTO bookings
                        (event_name, seat_number, booking_status, payment_status)
                    VALUES (?, ?, ?, ?)
                """, (event, "A2", "CANCELLED", "SUCCESS"))

                connection.execute("""
                    INSERT INTO bookings
                        (event_name, seat_number, booking_status, payment_status)
                    VALUES (?, ?, ?, ?)
                """, (event, "A3", "FAILED", "FAILED"))

                rows = connection.execute("""
                    SELECT booking_status FROM bookings
                    WHERE event_name = ?
                """, (event,)).fetchall()

                statuses = {row["booking_status"] for row in rows}
                passed = statuses == {"CONFIRMED", "CANCELLED", "FAILED"}
                message = (
                    "Booking statuses were saved correctly."
                    if passed else "Booking statuses were incorrect."
                )

            else:
                return {
                    "success": False,
                    "test_name": test_name,
                    "status": "NOT IMPLEMENTED",
                    "message": "Unknown test name."
                }, 400

            result = "PASS" if passed else "FAIL"

            # Test records mattum remove pannuvom.
            connection.execute(
                "DELETE FROM bookings WHERE event_name = ?",
                (event,)
            )

        return {
            "success": result == "PASS",
            "test_name": test_name,
            "status": result,
            "message": message
        }, 200

    except sqlite3.Error as error:
        return {
            "success": False,
            "test_name": test_name,
            "status": "FAIL",
            "message": str(error)
        }, 500


@app.route("/api/run-test", methods=["POST"])
def run_test():
    data = request.get_json(silent=True) or {}
    test_name = data.get("test_name", "")

    valid_tests = [
        "Search Results",
        "Seat Allocation",
        "Duplicate Booking",
        "Payment Failure",
        "Cancellation",
        "Refund",
        "Booking Status"
    ]

    if test_name not in valid_tests:
        return jsonify({
            "success": False,
            "status": "FAIL",
            "message": "Invalid test name."
        }), 400

    result, status_code = run_database_test(test_name)
    return jsonify(result), status_code


if __name__ == "__main__":
    init_db()
    print("Starting Software Testing Validation...")
    app.run(debug=True)