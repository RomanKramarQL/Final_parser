from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI()

# Подключаемся к PostgreSQL (используем переменную окружения из Railway)
DATABASE_URL = "postgresql://postgres:RfbptDYJEpZEzRuEsdFBPEFSJSSuopRh@postgres.railway.internal:5432/railway"

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
    cur.execute("SELECT * FROM drivers;")  # Замените `your_table` на имя таблицы
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