from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, datetime
from db import get_db

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"


# ================= JINJA GLOBALS =================
@app.context_processor
def inject_now():
    return {"now": datetime.now}


# ================= AUTH DECORATOR =================
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return fn(*args, **kwargs)
    return wrapper


# ================= SIGNUP =================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT id FROM users WHERE username=%s",
            (request.form["username"],)
        )
        if cur.fetchone():
            return render_template("signup.html", error="Username already exists")

        cur.execute(
            """
            INSERT INTO users (username, password_hash, is_admin)
            VALUES (%s,%s,%s)
            """,
            (
                request.form["username"],
                generate_password_hash(request.form["password"]),
                False
            )
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/login")

    return render_template("signup.html")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT * FROM users WHERE username=%s",
            (request.form["username"],)
        )
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session["user_id"] = user["id"]
            session["is_admin"] = bool(user["is_admin"])
            return redirect("/")

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


# ================= LOGOUT =================
@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/login")


# ================= DASHBOARD =================
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    today = date.today()
    current_month = today.strftime("%Y-%m")

    # ---------- ADD EXPENSE (POST) ----------
    if request.method == "POST":
        amount = float(request.form["amount"])

        if request.form["expense_date"]:
            expense_date = date.fromisoformat(request.form["expense_date"])
        else:
            expense_date = today

        month_key = expense_date.strftime("%Y-%m")

        cur.execute(
            """
            INSERT INTO expenses
            (title, category, amount, expense_date, user_id)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (
                request.form["title"],
                request.form["category"],
                amount,
                expense_date,
                session["user_id"]
            )
        )
        conn.commit()

        # ---- Budget check ONLY for popup ----
        cur.execute(
            """
            SELECT amount FROM budgets
            WHERE user_id=%s AND month=%s
            """,
            (session["user_id"], month_key)
        )
        budget = cur.fetchone()

        exceeded = False
        budget_amount = None
        total_spent = None

        if budget:
            budget_amount = float(budget["amount"])

            cur.execute(
                """
                SELECT SUM(amount) total
                FROM expenses
                WHERE user_id=%s
                  AND DATE_FORMAT(expense_date, '%Y-%m')=%s
                """,
                (session["user_id"], month_key)
            )
            total_spent = float(cur.fetchone()["total"] or 0)

            if total_spent > budget_amount:
                exceeded = True

        session["budget_alert"] = {
            "exceeded": exceeded,
            "budget": budget_amount,
            "spent": total_spent
        }

        return redirect("/")

    # ---------- ALWAYS FETCH BUDGET SUMMARY (GET) ----------
    cur.execute(
        """
        SELECT amount FROM budgets
        WHERE user_id=%s AND month=%s
        """,
        (session["user_id"], current_month)
    )
    budget = cur.fetchone()

    budget_summary = None
    if budget:
        cur.execute(
            """
            SELECT SUM(amount) total
            FROM expenses
            WHERE user_id=%s
              AND DATE_FORMAT(expense_date, '%Y-%m')=%s
            """,
            (session["user_id"], current_month)
        )
        spent = float(cur.fetchone()["total"] or 0)

        budget_summary = {
            "budget": float(budget["amount"]),
            "spent": spent,
            "exceeded": spent > float(budget["amount"])
        }

    # ---------- FETCH EXPENSES ----------
    cur.execute(
        """
        SELECT * FROM expenses
        WHERE user_id=%s
        ORDER BY expense_date DESC
        """,
        (session["user_id"],)
    )
    expenses = cur.fetchall()

    cur.execute("SELECT name FROM categories ORDER BY name")
    categories = cur.fetchall()

    alert = session.pop("budget_alert", None)

    cur.close()
    conn.close()

    return render_template(
        "index.html",
        expenses=expenses,
        categories=categories,
        budget_alert=alert,        # popup only
        budget_summary=budget_summary  # ALWAYS shown
    )


# ================= SET / UPDATE BUDGET =================
@app.route("/budget", methods=["POST"])
@login_required
def set_budget():
    month = request.form["month"]
    amount = request.form["amount"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO budgets (user_id, month, amount)
        VALUES (%s,%s,%s)
        ON DUPLICATE KEY UPDATE amount=%s
        """,
        (session["user_id"], month, amount, amount)
    )

    conn.commit()
    conn.close()
    return redirect("/")

#asdfghjkllmnbv
# ================= EDIT / DELETE EXPENSE =================
@app.route("/expense/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        cur.execute(
            """
            UPDATE expenses
            SET title=%s, category=%s,
                amount=%s, expense_date=%s
            WHERE id=%s AND user_id=%s
            """,
            (
                request.form["title"],
                request.form["category"],
                request.form["amount"],
                request.form["expense_date"],
                id,
                session["user_id"]
            )
        )
        conn.commit()
        return redirect("/")

    cur.execute(
        "SELECT * FROM expenses WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )
    expense = cur.fetchone()

    cur.execute("SELECT name FROM categories ORDER BY name")
    categories = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("edit_expense.html", expense=expense, categories=categories)


@app.route("/expense/delete/<int:id>")
@login_required
def delete_expense(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM expenses WHERE id=%s AND user_id=%s",
        (id, session["user_id"])
    )
    conn.commit()
    conn.close()
    return redirect("/")


# ================= CATEGORIES =================
@app.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        cur.execute(
            "INSERT IGNORE INTO categories (name) VALUES (%s)",
            (request.form["name"],)
        )
        conn.commit()

    cur.execute("SELECT * FROM categories ORDER BY name")
    cats = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("categories.html", categories=cats)


@app.route("/category/edit/<int:id>", methods=["POST"])
@login_required
def edit_category(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE categories SET name=%s WHERE id=%s",
        (request.form["name"], id)
    )
    conn.commit()
    conn.close()
    return redirect("/categories")


@app.route("/category/delete/<int:id>")
@login_required
def delete_category(id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM categories WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect("/categories")


# ================= CHARTS =================
@app.route("/charts")
@login_required
def charts():
    scope = request.args.get("scope", "user")
    period = request.args.get("period", "monthly")

    if scope == "master" and not session.get("is_admin"):
        return redirect("/charts?scope=user&period=" + period)

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    if period == "weekly":
        grp = "YEARWEEK(expense_date, 1)"
        lbl = grp
    elif period == "yearly":
        grp = "YEAR(expense_date)"
        lbl = grp
    elif period == "monthly":
        grp = "DATE_FORMAT(expense_date, '%Y-%m')"
        lbl = grp
    else:
        grp = "expense_date"
        lbl = grp

    if scope == "master":
        cur.execute("SELECT category, SUM(amount) total FROM expenses GROUP BY category")
        category_data = cur.fetchall()

        cur.execute(
            f"""
            SELECT {lbl} AS period, SUM(amount) total
            FROM expenses
            GROUP BY {grp}
            ORDER BY {grp}
            """
        )
        time_data = cur.fetchall()
    else:
        cur.execute(
            """
            SELECT category, SUM(amount) total
            FROM expenses
            WHERE user_id=%s
            GROUP BY category
            """,
            (session["user_id"],)
        )
        category_data = cur.fetchall()

        cur.execute(
            f"""
            SELECT {lbl} AS period, SUM(amount) total
            FROM expenses
            WHERE user_id=%s
            GROUP BY {grp}
            ORDER BY {grp}
            """,
            (session["user_id"],)
        )
        time_data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "charts.html",
        category_data=category_data,
        time_data=time_data,
        scope=scope,
        period=period,
        is_admin=session.get("is_admin", False)
    )
