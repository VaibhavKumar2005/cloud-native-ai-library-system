import os
from flask import Flask, jsonify
from flask_cors import CORS
import psycopg2
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Azure-Native AI Librarian Backend",
        "version": "1.0.0"
    })

@app.route('/health/db')
def db_check():
    status = {"postgres": "unknown", "mongo": "unknown"}
    
    # Check Postgres
    try:
        conn = psycopg2.connect(
            host="postgres", database="library_db", user="admin", password="devpassword"
        )
        conn.close()
        status["postgres"] = "connected"
    except Exception as e:
        status["postgres"] = f"failed: {str(e)}"

    # Check Mongo
    try:
        client = MongoClient("mongodb://admin:devpassword@mongo:27017/", serverSelectionTimeoutMS=2000)
        client.server_info()
        status["mongo"] = "connected"
    except Exception as e:
        status["mongo"] = f"failed: {str(e)}"

    return jsonify(status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)