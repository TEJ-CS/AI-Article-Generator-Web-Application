from datetime import datetime
from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from groq import Groq
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.pdfgen import canvas

app = Flask(__name__)

# ================= CONFIG =================
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///articles.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================= GROQ API =================
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ================= LOGIN MANAGER =================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ================= MODELS =================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))


class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(200))
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ================= LOAD USER =================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ================= AI FUNCTION =================
def generate_article(topic):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": f"Write a detailed article on {topic}"}
        ]
    )
    return response.choices[0].message.content


# ================= HOME =================
@app.route("/", methods=["GET", "POST"])
def home():
    article = None

    if request.method == "POST":
        topic = request.form["topic"]
        article = generate_article(topic)

        if current_user.is_authenticated:
            new_article = Article(
                topic=topic,
                content=article,
                user_id=current_user.id
            )
            db.session.add(new_article)
            db.session.commit()

    return render_template("index.html", article=article)


# ================= HISTORY =================
@app.route("/history")
@login_required
def history():
    articles = Article.query.filter_by(user_id=current_user.id).all()
    return render_template("history.html", articles=articles)


# ================= SAVE FILE =================
@app.route("/save", methods=["POST"])
def save():
    article = request.form["article"]
    format_type = request.form["format"]

    if format_type == "txt":
        file_path = "article.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(article)
        return send_file(file_path, as_attachment=True)

    elif format_type == "pdf":
        file_path = "article.pdf"
        c = canvas.Canvas(file_path)
        text = c.beginText(40, 800)

        for line in article.split("\n"):
            text.textLine(line)

        c.drawText(text)
        c.save()

        return send_file(file_path, as_attachment=True)


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            login_user(user)
            return redirect("/")

    return render_template("login.html")


# ================= SIGNUP =================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        hashed_pw = generate_password_hash(request.form["password"])

        new_user = User(
            username=request.form["username"],
            password=hashed_pw
        )

        db.session.add(new_user)
        db.session.commit()
        return redirect("/login")

    return render_template("signup.html")


# ================= LOGOUT =================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


# ================= CREATE DB =================
with app.app_context():
    db.create_all()


# ================= RUN =================

import webbrowser
from threading import Timer

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)