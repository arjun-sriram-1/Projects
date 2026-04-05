from flask import Flask, request, jsonify
import sqlite3
import joblib
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

model = joblib.load('fraud_model.pkl')


# ---------------- DB INIT ----------------
def init_db():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    ''')

    # TRANSACTIONS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            oldbalance REAL,
            newbalance REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # FRAUD LOG TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fraud_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER,
            prediction TEXT,
            risk REAL,
            FOREIGN KEY(transaction_id) REFERENCES transactions(id)
        )
    ''')

    # Insert default user if not exists
    cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES (1, 'Default User')")

    conn.commit()
    conn.close()


init_db()


# ---------------- PREDICT ----------------
@app.route('/predict', methods=['POST'])
def predict_fraud():
    data = request.json

    amount = float(data['amount'])
    oldbalance = float(data['oldbalance'])
    newbalance = float(data['newbalance'])

    prob = model.predict_proba([[amount, oldbalance, newbalance]])[0][1]
    risk = round(prob * 100, 2)
    prediction = "Fraud" if prob > 0.5 else "Not Fraud"

    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()

    # Insert into transactions
    cursor.execute('''
        INSERT INTO transactions (user_id, amount, oldbalance, newbalance)
        VALUES (1, ?, ?, ?)
    ''', (amount, oldbalance, newbalance))

    transaction_id = cursor.lastrowid

    # Insert into fraud_logs
    cursor.execute('''
        INSERT INTO fraud_logs (transaction_id, prediction, risk)
        VALUES (?, ?, ?)
    ''', (transaction_id, prediction, risk))

    conn.commit()
    conn.close()

    return jsonify({
        "prediction": prediction,
        "risk": risk
    })


# ---------------- GET HISTORY (JOIN 🔥) ----------------
@app.route('/transactions', methods=['GET'])
def get_transactions():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()

    # JOIN QUERY 🔥
    cursor.execute('''
        SELECT t.id, t.amount, t.oldbalance, t.newbalance,
               f.prediction, f.risk
        FROM transactions t
        JOIN fraud_logs f ON t.id = f.transaction_id
        ORDER BY t.id DESC
    ''')

    rows = cursor.fetchall()
    conn.close()

    data = []
    for row in rows:
        data.append({
            "id": row[0],
            "amount": row[1],
            "oldbalance": row[2],
            "newbalance": row[3],
            "prediction": row[4],
            "risk": row[5]
        })

    return jsonify(data)


# ---------------- STATS ----------------
@app.route('/stats', methods=['GET'])
def get_stats():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()

    # JOIN + AGGREGATION 🔥
    cursor.execute('''
        SELECT 
            COUNT(*),
            SUM(CASE WHEN f.prediction='Fraud' THEN 1 ELSE 0 END),
            SUM(CASE WHEN f.prediction='Not Fraud' THEN 1 ELSE 0 END)
        FROM fraud_logs f
    ''')

    result = cursor.fetchone()
    conn.close()

    total = result[0] if result[0] else 0
    fraud = result[1] if result[1] else 0
    legit = result[2] if result[2] else 0

    return jsonify({
        "total": total,
        "fraud": fraud,
        "legit": legit
    })


# ---------------- TOP RISK ----------------
@app.route('/top-transactions', methods=['GET'])
def top_transactions():
    conn = sqlite3.connect('transactions.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT t.id, t.amount, f.risk
        FROM transactions t
        JOIN fraud_logs f ON t.id = f.transaction_id
        ORDER BY f.risk DESC
        LIMIT 5
    ''')

    rows = cursor.fetchall()
    conn.close()

    data = []
    for row in rows:
        data.append({
            "id": row[0],
            "amount": row[1],
            "risk": row[2]
        })

    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)