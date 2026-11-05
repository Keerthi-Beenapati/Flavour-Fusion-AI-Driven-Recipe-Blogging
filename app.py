import os, sqlite3, json, re
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "flavour_fusion.db")
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLAVOUR_FUSION_SECRET", "change-this-secret-before-deployment")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024

SEED = [
("Creamy Tomato Basil Pasta","Italian","Easy",25,2,"vegetarian","pasta, tomato, basil, garlic, cream","A comforting weeknight pasta with a silky tomato-basil sauce.","Boil pasta in salted water. Sauté garlic in olive oil. Add chopped tomatoes and simmer 10 minutes. Stir in cream and basil. Toss with pasta and finish with parmesan.","https://images.unsplash.com/photo-147 pasta"),
("Chickpea Coconut Curry","Indian","Easy",35,4,"vegan","chickpeas, coconut milk, tomato, onion, curry powder","A fragrant, plant-based curry with a creamy coconut finish.","Sauté onion until soft. Add garlic and curry powder. Stir in tomatoes and chickpeas. Add coconut milk and simmer 20 minutes. Serve with rice and coriander.",""),
("Lemon Herb Salmon","Mediterranean","Medium",22,2,"gluten-free","salmon, lemon, parsley, garlic, olive oil","Bright lemon and fresh herbs keep this salmon simple and elegant.","Heat oven to 200°C. Mix lemon, garlic, parsley and olive oil. Coat salmon. Bake 12–15 minutes or until cooked through. Serve with vegetables.",""),
("Mango Overnight Oats","Breakfast","Easy",10,1,"vegetarian","oats, milk, yogurt, mango, chia seeds","A make-ahead breakfast with juicy mango and a creamy texture.","Combine oats, milk, yogurt and chia seeds in a jar. Refrigerate overnight. Top with diced mango before serving.",""),
("Crispy Vegetable Tacos","Mexican","Easy",30,3,"vegan","black beans, corn, bell pepper, avocado, tortillas","Colourful tacos with smoky vegetables and a fresh avocado topping.","Roast sliced peppers and corn with cumin and oil. Warm beans. Fill tortillas with vegetables and beans. Top with avocado, lime and coriander.",""),
("Peanut Butter Banana Smoothie","Drinks","Easy",5,1,"vegetarian","banana, peanut butter, milk, oats, cinnamon","A quick, filling smoothie for busy mornings.","Blend banana, peanut butter, milk, oats and a pinch of cinnamon until smooth. Add ice or more milk to adjust consistency.","")
]

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with connect_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS recipes(id INTEGER PRIMARY KEY, title TEXT NOT NULL, cuisine TEXT NOT NULL, difficulty TEXT NOT NULL, minutes INTEGER NOT NULL, servings INTEGER NOT NULL, diet TEXT NOT NULL, ingredients TEXT NOT NULL, description TEXT NOT NULL, instructions TEXT NOT NULL, author_id INTEGER, created_at TEXT NOT NULL, FOREIGN KEY(author_id) REFERENCES users(id) ON DELETE SET NULL);
        CREATE TABLE IF NOT EXISTS favorites(user_id INTEGER NOT NULL, recipe_id INTEGER NOT NULL, PRIMARY KEY(user_id, recipe_id), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS meal_plan(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, recipe_id INTEGER NOT NULL, plan_date TEXT NOT NULL, meal_type TEXT NOT NULL, UNIQUE(user_id, recipe_id, plan_date, meal_type), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE);
        """)
        count = db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
        if count == 0:
            now = datetime.utcnow().isoformat()
            for title,cuisine,diff,mins,servings,diet,ingredients,desc,instructions,_ in SEED:
                db.execute("INSERT INTO recipes(title,cuisine,difficulty,minutes,servings,diet,ingredients,description,instructions,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                           (title,cuisine,diff,mins,servings,diet,ingredients,desc,instructions,now))
init_db()

@app.before_request
def load_user():
    g.user = None
    if session.get("user_id"):
        with connect_db() as db:
            g.user = db.execute("SELECT id,name,email FROM users WHERE id=?", (session["user_id"],)).fetchone()

@app.context_processor
def common():
    return {"current_user": g.get("user"), "year": datetime.now().year}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not g.user:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def recipe_dict(row):
    d = dict(row)
    d["ingredient_list"] = [x.strip() for x in d["ingredients"].split(",") if x.strip()]
    d["steps"] = [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])", d["instructions"]) if x.strip()]
    return d

@app.route("/")
def home():
    q = request.args.get("q","").strip()
    cuisine = request.args.get("cuisine","").strip()
    diet = request.args.get("diet","").strip()
    max_time = request.args.get("max_time","").strip()
    sql = "SELECT * FROM recipes WHERE 1=1"
    params=[]
    if q:
        sql += " AND (title LIKE ? OR ingredients LIKE ? OR description LIKE ? OR cuisine LIKE ?)"
        params += [f"%{q}%"]*4
    if cuisine:
        sql += " AND cuisine=?"; params.append(cuisine)
    if diet:
        sql += " AND diet=?"; params.append(diet)
    if max_time.isdigit():
        sql += " AND minutes<=?"; params.append(int(max_time))
    sql += " ORDER BY id DESC"
    with connect_db() as db:
        recipes = [recipe_dict(r) for r in db.execute(sql,params).fetchall()]
        cuisines = [r[0] for r in db.execute("SELECT DISTINCT cuisine FROM recipes ORDER BY cuisine")]
        stats = {"recipes": db.execute("SELECT COUNT(*) FROM recipes").fetchone()[0],
                 "members": db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                 "saved": db.execute("SELECT COUNT(*) FROM favorites").fetchone()[0]}
        favs = set()
        if g.user:
            favs = {r[0] for r in db.execute("SELECT recipe_id FROM favorites WHERE user_id=?", (g.user["id"],))}
    return render_template("index.html", recipes=recipes, cuisines=cuisines, q=q, selected_cuisine=cuisine, selected_diet=diet, max_time=max_time, favs=favs, stats=stats)

@app.route("/recipe/<int:recipe_id>")
def recipe_detail(recipe_id):
    with connect_db() as db:
        row = db.execute("SELECT r.*, u.name AS author FROM recipes r LEFT JOIN users u ON u.id=r.author_id WHERE r.id=?", (recipe_id,)).fetchone()
        if not row:
            flash("Recipe not found.", "error"); return redirect(url_for("home"))
        recipe = recipe_dict(row)
        favorite = bool(g.user and db.execute("SELECT 1 FROM favorites WHERE user_id=? AND recipe_id=?", (g.user["id"],recipe_id)).fetchone())
    return render_template("recipe.html", recipe=recipe, favorite=favorite)

@app.route("/register", methods=["GET","POST"])
def register():
    if g.user: return redirect(url_for("home"))
    if request.method == "POST":
        name=request.form.get("name","").strip()
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        if len(name)<2 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$",email) or len(password)<8:
            flash("Enter a name, valid email, and password with at least 8 characters.", "error")
        else:
            try:
                with connect_db() as db:
                    cur=db.execute("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
                                   (name,email,generate_password_hash(password),datetime.utcnow().isoformat()))
                    session["user_id"]=cur.lastrowid
                flash("Welcome to Flavour Fusion!", "success"); return redirect(url_for("home"))
            except sqlite3.IntegrityError:
                flash("An account with that email already exists.", "error")
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET","POST"])
def login():
    if g.user: return redirect(url_for("home"))
    if request.method == "POST":
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        with connect_db() as db: user=db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"],password):
            session.clear(); session["user_id"]=user["id"]
            flash("You are signed in.", "success")
            target=request.args.get("next","")
            return redirect(target if target.startswith("/") and not target.startswith("//") else url_for("home"))
        flash("Email or password is incorrect.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear(); flash("You have signed out.", "success"); return redirect(url_for("home"))

@app.route("/recipe/new", methods=["GET","POST"])
@login_required
def new_recipe():
    if request.method=="POST":
        data = {k:request.form.get(k,"").strip() for k in ["title","cuisine","difficulty","diet","ingredients","description","instructions"]}
        try: minutes=max(1,min(1440,int(request.form.get("minutes","30")))); servings=max(1,min(50,int(request.form.get("servings","2"))))
        except ValueError: minutes,servings=30,2
        if not all(data.values()):
            flash("Please complete every field.", "error")
        else:
            with connect_db() as db:
                cur=db.execute("""INSERT INTO recipes(title,cuisine,difficulty,minutes,servings,diet,ingredients,description,instructions,author_id,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",(data["title"],data["cuisine"],data["difficulty"],minutes,servings,data["diet"],data["ingredients"],data["description"],data["instructions"],g.user["id"],datetime.utcnow().isoformat()))
                rid=cur.lastrowid
            flash("Your recipe has been published.", "success"); return redirect(url_for("recipe_detail",recipe_id=rid))
    return render_template("recipe_form.html")

@app.route("/favorite/<int:recipe_id>", methods=["POST"])
@login_required
def favorite(recipe_id):
    with connect_db() as db:
        exists=db.execute("SELECT 1 FROM recipes WHERE id=?",(recipe_id,)).fetchone()
        if not exists: return jsonify(ok=False,error="Recipe not found"),404
        row=db.execute("SELECT 1 FROM favorites WHERE user_id=? AND recipe_id=?",(g.user["id"],recipe_id)).fetchone()
        if row:
            db.execute("DELETE FROM favorites WHERE user_id=? AND recipe_id=?",(g.user["id"],recipe_id)); saved=False
        else:
            db.execute("INSERT INTO favorites(user_id,recipe_id) VALUES(?,?)",(g.user["id"],recipe_id)); saved=True
    if request.headers.get("X-Requested-With")=="XMLHttpRequest": return jsonify(ok=True,saved=saved)
    flash("Recipe saved." if saved else "Recipe removed from saved recipes.", "success")
    return redirect(request.referrer or url_for("home"))

@app.route("/saved")
@login_required
def saved():
    with connect_db() as db:
        rows=db.execute("SELECT r.* FROM recipes r JOIN favorites f ON f.recipe_id=r.id WHERE f.user_id=? ORDER BY r.title",(g.user["id"],)).fetchall()
    return render_template("saved.html", recipes=[recipe_dict(r) for r in rows])

@app.route("/planner", methods=["GET","POST"])
@login_required
def planner():
    if request.method=="POST":
        recipe_id=request.form.get("recipe_id","")
        plan_date=request.form.get("plan_date","")
        meal_type=request.form.get("meal_type","Dinner")
        try: datetime.strptime(plan_date,"%Y-%m-%d")
        except ValueError: flash("Choose a valid date.", "error"); return redirect(url_for("planner"))
        with connect_db() as db:
            valid=db.execute("SELECT 1 FROM recipes WHERE id=?",(recipe_id,)).fetchone()
            if valid:
                db.execute("INSERT OR IGNORE INTO meal_plan(user_id,recipe_id,plan_date,meal_type) VALUES(?,?,?,?)",(g.user["id"],recipe_id,plan_date,meal_type))
                flash("Meal added to your planner.", "success")
        return redirect(url_for("planner"))
    with connect_db() as db:
        plans=db.execute("SELECT mp.*,r.title,r.minutes FROM meal_plan mp JOIN recipes r ON r.id=mp.recipe_id WHERE mp.user_id=? ORDER BY plan_date, meal_type",(g.user["id"],)).fetchall()
        recipes=db.execute("SELECT id,title FROM recipes ORDER BY title").fetchall()
    return render_template("planner.html", plans=plans, recipes=recipes, today=datetime.now().strftime("%Y-%m-%d"))

@app.route("/planner/delete/<int:plan_id>", methods=["POST"])
@login_required
def delete_plan(plan_id):
    with connect_db() as db: db.execute("DELETE FROM meal_plan WHERE id=? AND user_id=?",(plan_id,g.user["id"]))
    flash("Meal removed from planner.", "success"); return redirect(url_for("planner"))

@app.route("/generate", methods=["GET","POST"])
def generate():
    result=None
    if request.method=="POST":
        ingredients=request.form.get("ingredients","").strip()
        cuisine=request.form.get("cuisine","Any").strip()
        diet=request.form.get("diet","Any").strip()
        if len(ingredients)<2:
            flash("Enter at least one ingredient.", "error")
        else:
            key=os.environ.get("GEMINI_API_KEY","").strip()
            if key:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=key)
                    model=genai.GenerativeModel("gemini-2.0-flash")
                    prompt=f"""Create one practical recipe using these available ingredients: {ingredients}. Cuisine preference: {cuisine}. Dietary preference: {diet}. Return plain text with: title, short description, preparation/cooking time, servings, ingredients with quantities, numbered instructions, substitutions, and storage tips. Avoid claiming medical benefits. Respect the dietary preference."""
                    result=model.generate_content(prompt).text
                except Exception:
                    result=fallback_recipe(ingredients,cuisine,diet)
                    flash("AI provider was unavailable, so a local recipe draft was created instead.", "info")
            else:
                result=fallback_recipe(ingredients,cuisine,diet)
                flash("Showing a local recipe draft. Add GEMINI_API_KEY in your environment to enable Gemini-generated recipes.", "info")
    return render_template("generate.html", result=result)

def fallback_recipe(ingredients,cuisine,diet):
    items=[x.strip() for x in ingredients.split(",") if x.strip()]
    return f"""YOUR {cuisine.upper()}-INSPIRED RECIPE DRAFT

Concept
A flexible, home-cooked dish built around the ingredients you have. Dietary preference: {diet}.

Ingredients to use
""" + "\n".join(f"• {x}" for x in items) + """

Method
1. Wash and prepare all ingredients. Cut vegetables into similar-sized pieces so they cook evenly.
2. Heat a little oil in a pan. Add aromatic ingredients first, if available, and cook until fragrant.
3. Add the remaining ingredients in order of cooking time. Add a splash of water or stock if the pan becomes dry.
4. Season gradually with salt, pepper, herbs or spices that suit your preference. Cook until all ingredients are safely cooked and tender.
5. Taste, adjust seasoning, and serve warm. For a balanced meal, pair with rice, bread, or a fresh salad where appropriate.

Chef's note
This is a starter draft, not a tested recipe. Adjust cooking times to the ingredients and verify food is thoroughly cooked."""

@app.errorhandler(404)
def not_found(e): return render_template("error.html", code=404, message="We couldn't find that page."),404
@app.errorhandler(500)
def server_error(e): return render_template("error.html", code=500, message="Something went wrong. Please try again."),500

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG","0")=="1", host="127.0.0.1", port=int(os.environ.get("PORT","5000")))
