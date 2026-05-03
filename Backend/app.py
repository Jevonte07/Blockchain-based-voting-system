from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from blockchain import Blockchain
from datetime import datetime
from functools import wraps
import sqlite3
import hashlib
import secrets
import time

# -------------------------------------------------
# APP CONFIG
# -------------------------------------------------
app = Flask(__name__, static_folder="../admin-panel")
app.secret_key = secrets.token_hex(32)

CORS(app, supports_credentials=True)

DB = "voting.db"

# -------------------------------------------------
# BLOCKCHAIN
# -------------------------------------------------
bc = Blockchain()

# -------------------------------------------------
# DATABASE
# -------------------------------------------------
def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS candidates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS votes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter TEXT UNIQUE,
        candidate TEXT,
        voted_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins(
        username TEXT PRIMARY KEY,
        password TEXT
    )
    """)

    conn.commit()

    # default admin
    cur.execute("SELECT * FROM admins WHERE username='admin'")
    row = cur.fetchone()

    if row is None:
        password_hash = hashlib.sha256("1234".encode()).hexdigest()
        cur.execute(
            "INSERT INTO admins(username,password) VALUES(?,?)",
            ("admin", password_hash)
        )
        conn.commit()

    conn.close()


init_db()

# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def get_setting(key):
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()

    conn.close()

    if row:
        return row["value"]
    return ""


def set_setting(key, value):
    conn = db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO settings(key,value)
    VALUES(?,?)
    ON CONFLICT(key)
    DO UPDATE SET value=excluded.value
    """, (key, value))

    conn.commit()
    conn.close()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return jsonify({"msg": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


last_vote_time = {}

# -------------------------------------------------
# STATIC FILES
# -------------------------------------------------
@app.route('/')
def home():
    return send_from_directory("../admin-panel", "index.html")


@app.route('/<path:path>')
def files(path):
    return send_from_directory("../admin-panel", path)

# -------------------------------------------------
# LOGIN
# -------------------------------------------------
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json(force=True, silent=True)

        if not data:
            return jsonify({"msg": "fail"})

        user = str(data.get("user", "")).strip()
        password = str(data.get("pass", "")).strip()

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM admins WHERE username=? AND password=?",
            (user, password_hash)
        )

        row = cur.fetchone()
        conn.close()

        if row:
            session["admin"] = user
            return jsonify({"msg": "success"})
        else:
            return jsonify({"msg": "fail"})

    except Exception as e:
        print("LOGIN ERROR:", e)
        return jsonify({"msg": "fail"})


@app.route('/logout')
def logout():
    session.clear()
    return jsonify({"msg": "logout"})

# -------------------------------------------------
# CANDIDATES
# -------------------------------------------------
@app.route('/add_candidate', methods=['POST'])
@login_required
def add_candidate():

    data = request.get_json()
    name = str(data.get("name", "")).strip()

    if name == "":
        return jsonify({"msg": "Enter candidate name"})

    conn = db()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO candidates(name) VALUES(?)",
            (name,)
        )
        conn.commit()
    except:
        conn.close()
        return jsonify({"msg": "Candidate exists"})

    conn.close()
    return jsonify({"msg": "added"})


@app.route('/candidates')
def candidates():

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT name FROM candidates ORDER BY id")
    rows = cur.fetchall()

    conn.close()

    return jsonify([r["name"] for r in rows])


@app.route('/delete/<name>')
@login_required
def delete_candidate(name):

    conn = db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM candidates WHERE name=?",
        (name,)
    )

    conn.commit()
    conn.close()

    return jsonify({"msg": "deleted"})

# -------------------------------------------------
# TIME SETTINGS
# -------------------------------------------------
@app.route('/set_time', methods=['POST'])
@login_required
def set_time():

    data = request.get_json()

    start = data.get("start", "")
    end = data.get("end", "")

    set_setting("start_time", start)
    set_setting("end_time", end)

    return jsonify({"msg": "saved"})


@app.route('/get_time')
def get_time():

    return jsonify({
        "start": get_setting("start_time"),
        "end": get_setting("end_time")
    })

# -------------------------------------------------
# VOTE
# -------------------------------------------------
@app.route('/vote', methods=['POST'])
def vote():

    try:
        data = request.get_json()

        voter = str(data.get("voter", "")).strip().lower()
        candidate = str(data.get("candidate", "")).strip()
        biometric = data.get("biometric", False)

        if voter == "":
            return jsonify({"msg": "Enter Voter ID"})

        if biometric != True:
            return jsonify({"msg": "Fingerprint required"})

        start_time = get_setting("start_time")
        end_time = get_setting("end_time")

        if start_time == "" or end_time == "":
            return jsonify({"msg": "Voting time not set"})

        now = datetime.now()
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)

        if now < start:
            return jsonify({"msg": "Voting not started"})

        if now > end:
            return jsonify({"msg": "Voting ended"})

        # spam protection
        current = time.time()

        if voter in last_vote_time:
            if current - last_vote_time[voter] < 3:
                return jsonify({"msg": "Wait and retry"})

        last_vote_time[voter] = current

        # candidate exists
        conn = db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM candidates WHERE name=?",
            (candidate,)
        )

        row = cur.fetchone()

        if row is None:
            conn.close()
            return jsonify({"msg": "Invalid Candidate"})

        # already voted
        cur.execute(
            "SELECT * FROM votes WHERE voter=?",
            (voter,)
        )

        row = cur.fetchone()

        if row:
            conn.close()
            return jsonify({"msg": "Already voted"})

        # blockchain valid
        if not bc.is_chain_valid():
            conn.close()
            return jsonify({"msg": "Blockchain Error"})

        # save vote
        cur.execute(
            "INSERT INTO votes(voter,candidate,voted_at) VALUES(?,?,?)",
            (
                voter,
                candidate,
                datetime.now().isoformat()
            )
        )

        conn.commit()
        conn.close()

        # blockchain record
        bc.add_vote(voter, candidate)

        previous_block = bc.get_previous_block()
        previous_hash = bc.hash(previous_block)

        bc.create_block(previous_hash)

        return jsonify({"msg": "Vote Success"})

    except Exception as e:
        print("VOTE ERROR:", e)
        return jsonify({"msg": "Vote Failed"})

# -------------------------------------------------
# RESULTS
# -------------------------------------------------
@app.route('/results')
def results():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    SELECT candidate, COUNT(*) as total
    FROM votes
    GROUP BY candidate
    """)

    rows = cur.fetchall()

    conn.close()

    data = {}

    for row in rows:
        data[row["candidate"]] = row["total"]

    return jsonify(data)

# -------------------------------------------------
# WINNER
# -------------------------------------------------
@app.route('/winner')
def winner():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    SELECT candidate, COUNT(*) as total
    FROM votes
    GROUP BY candidate
    ORDER BY total DESC
    LIMIT 1
    """)

    row = cur.fetchone()

    conn.close()

    if row:
        return jsonify({
            "winner": row["candidate"],
            "votes": row["total"]
        })

    return jsonify({
        "winner": "No Votes",
        "votes": 0
    })

# -------------------------------------------------
# BLOCKCHAIN
# -------------------------------------------------
@app.route('/chain')
def chain():

    return jsonify({
        "length": len(bc.chain),
        "chain": bc.chain
    })


@app.route('/validate')
def validate():

    if bc.is_chain_valid():
        return jsonify({"msg": "Blockchain Valid"})
    else:
        return jsonify({"msg": "Blockchain Tampered"})

# -------------------------------------------------
# RUN
# -------------------------------------------------
app.run(host="0.0.0.0", port=5000)