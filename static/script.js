const dbStatus = document.getElementById("dbStatus");
const bookingForm = document.getElementById("bookingForm");
const bookingMessage = document.getElementById("bookingMessage");
const searchForm = document.getElementById("searchForm");
const searchText = document.getElementById("searchText");
const bookingResults = document.getElementById("bookingResults");


async function checkDatabase() {
    try {
        const response = await fetch("/api/db-status");
        const data = await response.json();

        dbStatus.textContent = data.success
            ? "SQLite Connected"
            : "Database Error";

        dbStatus.style.background = data.success ? "#dcfce7" : "#fee2e2";
        dbStatus.style.color = data.success ? "#166534" : "#991b1b";
    } catch (error) {
        dbStatus.textContent = "Server Not Connected";
    }
}


bookingForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const eventName = document.getElementById("eventName").value.trim();
    const seatNumber = document.getElementById("seatNumber").value.trim();

    try {
        const response = await fetch("/api/bookings", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                event_name: eventName,
                seat_number: seatNumber
            })
        });

        const data = await response.json();

        bookingMessage.textContent = data.message;
        bookingMessage.style.color = data.success ? "green" : "red";

        if (data.success) {
            bookingForm.reset();
            loadBookings();
        }
    } catch (error) {
        bookingMessage.textContent = "Server connection failed.";
        bookingMessage.style.color = "red";
    }
});


async function loadBookings(search = "") {
    try {
        const response = await fetch(
            "/api/bookings?search=" + encodeURIComponent(search)
        );

        const data = await response.json();
        bookingResults.replaceChildren();

        if (!data.bookings.length) {
            const message = document.createElement("p");
            message.textContent = "No bookings found.";
            bookingResults.appendChild(message);
            return;
        }

        const table = document.createElement("table");
        const headings = [
            "ID", "Event", "Seat", "Booking Status",
            "Payment Status", "Refund Status"
        ];

        const thead = document.createElement("thead");
        const headerRow = document.createElement("tr");

        headings.forEach(function (heading) {
            const th = document.createElement("th");
            th.textContent = heading;
            headerRow.appendChild(th);
        });

        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");

        data.bookings.forEach(function (booking) {
            const row = document.createElement("tr");

            [
                booking.id,
                booking.event_name,
                booking.seat_number,
                booking.booking_status,
                booking.payment_status,
                booking.refund_status
            ].forEach(function (value) {
                const td = document.createElement("td");
                td.textContent = value;
                row.appendChild(td);
            });

            tbody.appendChild(row);
        });

        table.appendChild(tbody);
        bookingResults.appendChild(table);

    } catch (error) {
        bookingResults.textContent = "Unable to load bookings.";
    }
}


searchForm.addEventListener("submit", function (event) {
    event.preventDefault();
    loadBookings(searchText.value.trim());
});


document.getElementById("showAllButton").addEventListener("click", function () {
    searchText.value = "";
    loadBookings();
});


document.querySelectorAll(".run-test").forEach(function (button) {
    button.addEventListener("click", async function () {
        const testName = button.dataset.test;
        const resultId = "result-" +
            testName.toLowerCase().replaceAll(" ", "-");

        const resultElement = document.getElementById(resultId);

        button.disabled = true;
        resultElement.className = "test-result";
        resultElement.textContent = "Testing...";

        try {
            const response = await fetch("/api/run-test", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    test_name: testName
                })
            });

            const data = await response.json();

            resultElement.textContent =
                data.status + " - " + data.message;

            if (data.status === "PASS") {
                resultElement.className = "test-result pass";
            } else if (data.status === "FAIL") {
                resultElement.className = "test-result fail";
            } else {
                resultElement.className = "test-result error";
            }

        } catch (error) {
            resultElement.textContent =
                "ERROR - Unable to connect to the server.";
            resultElement.className = "test-result error";
        } finally {
            button.disabled = false;
        }
    });
});


checkDatabase();
loadBookings();
