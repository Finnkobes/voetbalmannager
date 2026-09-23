from flask import Flask, render_template
import webbrowser
from threading import Timer

app = Flask(__name__)


clubs = [
    {
        "naam": "Ajax",
        "stad": "Amsterdam",
        "rating": 82
    },
    {
        "naam": "PSV",
        "stad": "Eindhoven",
        "rating": 81
    },
    {
        "naam": "Feyenoord",
        "stad": "Rotterdam",
        "rating": 80
    },
    {
        "naam": "FC Twente",
        "stad": "Enschede",
        "rating": 74
    },
    {
        "naam": "AZ",
        "stad": "Alkmaar",
        "rating": 73
    },
    {
        "naam": "FC Utrecht",
        "stad": "Utrecht",
        "rating": 70
    }
]


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/clubs")
def clubs_page():
    return render_template("clubs.html", clubs=clubs)


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")


if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)