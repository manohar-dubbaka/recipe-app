from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

# ---------------------- PATHS ----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # backend/
DB = os.path.join(BASE_DIR, "recipes.db")

# ---------------------- APP ----------------------
app = Flask(__name__)
CORS(app)

# ---------------------- DATABASE ----------------------
def init_db():
    with sqlite3.connect(DB, timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            owner_id INTEGER,
            image_base64 TEXT,
            FOREIGN KEY (owner_id) REFERENCES users(id)
        )
        """)

        conn.commit()


# 🔥 GUARANTEED TO RUN ON RENDER & LOCALLY
@app.before_first_request
def setup_database():
    init_db()


# ---------------------- FRONTEND ----------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------- REGISTER ----------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Missing username or password"}), 400

    try:
        with sqlite3.connect(DB, timeout=10) as conn:
            c = conn.cursor()
            hashed_password = generate_password_hash(password)
            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            user_id = c.lastrowid

        return jsonify({"success": True, "message": "Registered", "user_id": user_id}), 200

    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "User already exists"}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ---------------------- LOGIN ----------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Missing username or password"}), 400

    try:
        with sqlite3.connect(DB, timeout=10) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, password FROM users WHERE username=?",
                (username,)
            )
            user = c.fetchone()

        if not user:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        user_id, stored_hash = user

        if not check_password_hash(stored_hash, password):
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        return jsonify({"success": True, "message": "Login success", "user_id": user_id}), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ---------------------- ADD RECIPE ----------------------
@app.route("/add_recipe", methods=["POST"])
def add_recipe():
    data = request.json or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    owner_id = data.get("owner_id")
    image_base64 = data.get("image_base64")

    if not title or owner_id is None:
        return jsonify({"success": False, "message": "Missing title or owner_id"}), 400

    with sqlite3.connect(DB, timeout=10) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO recipes (title, description, owner_id, image_base64) VALUES (?, ?, ?, ?)",
            (title, description, owner_id, image_base64)
        )
        recipe_id = c.lastrowid

    return jsonify({"success": True, "message": "Recipe added", "id": recipe_id}), 200


# ---------------------- GET ALL RECIPES ----------------------
@app.route("/recipes", methods=["GET"])
def get_recipes():
    with sqlite3.connect(DB, timeout=10) as conn:
        c = conn.cursor()
        c.execute("""
        SELECT r.id, r.title, r.description, r.image_base64, u.username
        FROM recipes r
        JOIN users u ON r.owner_id = u.id
        ORDER BY r.id DESC
        """)
        rows = c.fetchall()

    return jsonify([
        {
            "id": r[0],
            "title": r[1],
            "description": r[2],
            "image_base64": r[3],
            "owner": r[4]
        } for r in rows
    ]), 200


# ---------------------- GET MY RECIPES ----------------------
@app.route("/my_recipes/<int:user_id>", methods=["GET"])
def get_my_recipes(user_id):
    with sqlite3.connect(DB, timeout=10) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, title, description, image_base64 FROM recipes WHERE owner_id=? ORDER BY id DESC",
            (user_id,)
        )
        rows = c.fetchall()

    return jsonify([
        {"id": r[0], "title": r[1], "description": r[2], "image_base64": r[3]}
        for r in rows
    ]), 200


# ---------------------- EDIT RECIPE ----------------------
@app.route("/edit_recipe/<int:recipe_id>/<int:owner_id>", methods=["PUT"])
def edit_recipe(recipe_id, owner_id):
    data = request.json or {}
    title = data.get("title")
    description = data.get("description")
    image_base64 = data.get("image_base64")

    with sqlite3.connect(DB, timeout=10) as conn:
        c = conn.cursor()
        c.execute("SELECT owner_id FROM recipes WHERE id=?", (recipe_id,))
        row = c.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Recipe not found"}), 404
        if row[0] != owner_id:
            return jsonify({"success": False, "message": "Not allowed"}), 403

        if image_base64 is not None:
            c.execute(
                "UPDATE recipes SET title=?, description=?, image_base64=? WHERE id=?",
                (title, description, image_base64, recipe_id)
            )
        else:
            c.execute(
                "UPDATE recipes SET title=?, description=? WHERE id=?",
                (title, description, recipe_id)
            )

    return jsonify({"success": True, "message": "Recipe updated"}), 200


# ---------------------- DELETE RECIPE ----------------------
@app.route("/delete_recipe/<int:recipe_id>/<int:owner_id>", methods=["DELETE"])
def delete_recipe(recipe_id, owner_id):
    with sqlite3.connect(DB, timeout=10) as conn:
        c = conn.cursor()
        c.execute("SELECT owner_id FROM recipes WHERE id=?", (recipe_id,))
        row = c.fetchone()

        if not row:
            return jsonify({"success": False, "message": "Recipe not found"}), 404
        if row[0] != owner_id:
            return jsonify({"success": False, "message": "Not allowed"}), 403

        c.execute("DELETE FROM recipes WHERE id=?", (recipe_id,))

    return jsonify({"success": True, "message": "Recipe deleted"}), 200


# ---------------------- RUN ----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
