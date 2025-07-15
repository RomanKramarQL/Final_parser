from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI()

# Подключаемся к PostgreSQL 
DATABASE_URL = "postgresql://postgres:password@81.94.158.73:5432/drivers_qrx"

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

@app.get("/")
def read_root():
    return {"message": "Hello, Railway!"}

@app.get("/api/data")
def get_data():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM drivers;")  
    data = cur.fetchall()
    conn.close()
    return {"data": data}

@app.get("/check_db")
def check_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()
        return {"status": "Database connection OK"}
    except Exception as e:
        return {"error": str(e)}, 500
