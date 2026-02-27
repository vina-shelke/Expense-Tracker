import mysql.connector
import os
import time
from werkzeug.security import generate_password_hash


def get_db():
    for _ in range(10):
        try:
            conn = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME")
            )
            cur = conn.cursor()

            # USERS
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE
            )
            """)

            # CATEGORIES
            cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL
            )
            """)

            # EXPENSES
            cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255),
                category VARCHAR(100),
                amount DECIMAL(10,2),
                expense_date DATE,
                user_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # BUDGETS (monthly per user)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                month VARCHAR(7) NOT NULL, -- YYYY-MM
                amount DECIMAL(10,2) NOT NULL,
                UNIQUE KEY unique_user_month (user_id, month)
            )
            """)

            # DEFAULT ADMIN
            cur.execute("SELECT COUNT(*) FROM users")
            if cur.fetchone()[0] == 0:
                cur.execute(
                    """
                    INSERT INTO users (username, password_hash, is_admin)
                    VALUES (%s,%s,%s)
                    """,
                    ("admin", generate_password_hash("Admin@123"), True)
                )

            conn.commit()
            cur.close()
            return conn

        except:
            time.sleep(3)

    raise Exception("Database connection failed")
