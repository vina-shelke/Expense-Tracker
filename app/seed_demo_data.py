import random
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from db import get_db   # 👈 IMPORTANT: reuse db.py


DEMO_USERS = [
    {"username": "rahul.patil", "password": "Rahul@123", "is_admin": False},
    {"username": "priya.sharma", "password": "Priya@123", "is_admin": False},
    {"username": "amit.verma", "password": "Amit@123", "is_admin": False},
    {"username": "admin", "password": "Admin@123", "is_admin": True},
]

CATEGORIES = [
    "Food",
    "Travel",
    "Rent",
    "Groceries",
    "Electricity",
    "Mobile Recharge",
    "Fuel",
    "Shopping"
]

TITLES = [
    "Zomato Order",
    "Swiggy Dinner",
    "BigBasket Groceries",
    "Petrol Pump",
    "Electricity Bill",
    "Jio Recharge",
    "Amazon Shopping",
    "Auto Rickshaw",
    "Metro Card Recharge"
]


def seed_users_and_expenses():
    # 👇 This guarantees tables exist
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    print("\n🔹 Seeding users...\n")

    user_ids = {}

    for user in DEMO_USERS:
        cur.execute("SELECT id FROM users WHERE username=%s", (user["username"],))
        existing = cur.fetchone()

        if existing:
            user_ids[user["username"]] = existing["id"]
            print(f"✔ User exists: {user['username']}")
            continue

        cur.execute(
            """
            INSERT INTO users (username, password_hash, is_admin)
            VALUES (%s,%s,%s)
            """,
            (
                user["username"],
                generate_password_hash(user["password"]),
                user["is_admin"]
            )
        )
        user_ids[user["username"]] = cur.lastrowid

        print(f"✔ Created user: {user['username']} | Password: {user['password']}")

    print("\n🔹 Seeding categories...\n")
    for cat in CATEGORIES:
        cur.execute(
            "INSERT IGNORE INTO categories (name) VALUES (%s)",
            (cat,)
        )

    print("\n🔹 Seeding expenses (last 4 months)...\n")

    today = date.today()
    start_date = today - timedelta(days=120)

    for username, user_id in user_ids.items():
        if username == "admin":
            continue  # optional: skip admin expenses

        cur.execute("SELECT COUNT(*) AS cnt FROM expenses WHERE user_id=%s", (user_id,))
        if cur.fetchone()["cnt"] > 0:
            print(f"✔ Expenses already exist for {username}")
            continue

        for i in range(120):
            expense_date = start_date + timedelta(days=i)

            if random.choice([True, False]):
                cur.execute(
                    """
                    INSERT INTO expenses (title, category, amount, expense_date, user_id)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (
                        random.choice(TITLES),
                        random.choice(CATEGORIES),
                        round(random.uniform(80, 2500), 2),
                        expense_date,
                        user_id
                    )
                )

        print(f"✔ Seeded expenses for {username}")

    conn.commit()
    cur.close()
    conn.close()

    print("\n✅ SEEDING COMPLETE\n")


if __name__ == "__main__":
    seed_users_and_expenses()
