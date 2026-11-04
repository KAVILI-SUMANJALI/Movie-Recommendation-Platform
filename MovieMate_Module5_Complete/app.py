import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "movie_platform.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")
app.config["DATABASE"] = DATABASE


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(app.config["DATABASE"])
    db.execute("PRAGMA foreign_keys = ON")

    # Module 1: user accounts and profiles
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            favorite_genres TEXT DEFAULT '',
            bio TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Module 2: movie catalog
    db.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            genre TEXT NOT NULL,
            release_year INTEGER,
            director TEXT DEFAULT '',
            description TEXT DEFAULT '',
            poster_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Module 2: each user's watchlist / viewing history
    db.execute("""
        CREATE TABLE IF NOT EXISTS watch_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Want to Watch'
                CHECK(status IN ('Want to Watch', 'Watched')),
            watched_on TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, movie_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(movie_id) REFERENCES movies(id) ON DELETE CASCADE
        )
    """)

    # Module 3: user movie ratings (one rating per user and movie)
    db.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, movie_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(movie_id) REFERENCES movies(id) ON DELETE CASCADE
        )
    """)

    # Module 4: movie reviews and sentiment-analysis results
    db.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            movie_id INTEGER NOT NULL,
            review_text TEXT NOT NULL,
            sentiment TEXT NOT NULL CHECK(sentiment IN ('Positive', 'Negative', 'Neutral')),
            compound_score REAL NOT NULL,
            positive_score REAL NOT NULL,
            neutral_score REAL NOT NULL,
            negative_score REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(movie_id) REFERENCES movies(id) ON DELETE CASCADE
        )
    """)

    # Insert sample movies only when the catalog is empty.
    count = db.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    if count == 0:
        sample_movies = [
            ("Inception", "Sci-Fi, Thriller", 2010, "Christopher Nolan",
             "A skilled thief enters people's dreams to steal and plant ideas.", ""),
            ("The Dark Knight", "Action, Crime, Drama", 2008, "Christopher Nolan",
             "Batman faces the Joker, a criminal mastermind who creates chaos in Gotham.", ""),
            ("Interstellar", "Sci-Fi, Adventure, Drama", 2014, "Christopher Nolan",
             "Explorers travel through a wormhole in search of a future for humanity.", ""),
            ("3 Idiots", "Comedy, Drama", 2009, "Rajkumar Hirani",
             "Three engineering students learn about friendship, education and following their passion.", ""),
            ("Dangal", "Biography, Drama, Sport", 2016, "Nitesh Tiwari",
             "A former wrestler trains his daughters to become competitive wrestlers.", ""),
            ("Baahubali: The Beginning", "Action, Drama, Fantasy", 2015, "S. S. Rajamouli",
             "A young man discovers his royal heritage and a hidden kingdom.", ""),
            ("RRR", "Action, Drama", 2022, "S. S. Rajamouli",
             "Two revolutionaries form a powerful friendship during the pre-independence era.", ""),
            ("The Shawshank Redemption", "Drama", 1994, "Frank Darabont",
             "Two prisoners form a lasting friendship while holding on to hope.", ""),
            ("Finding Nemo", "Animation, Adventure, Comedy", 2003, "Andrew Stanton",
             "A clownfish crosses the ocean to find his missing son.", ""),
            ("The Matrix", "Sci-Fi, Action", 1999, "Lana and Lilly Wachowski",
             "A computer programmer discovers that reality is not what it seems.", "")
        ]
        db.executemany("""
            INSERT INTO movies (title, genre, release_year, director, description, poster_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_movies)

    db.commit()
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


# ---------------- Module 1: Authentication & Profile Management ----------------

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([full_name, username, email, password, confirm_password]):
            flash("Please fill in all required fields.", "danger")
        elif len(username) < 3:
            flash("Username must contain at least 3 characters.", "danger")
        elif "@" not in email or "." not in email:
            flash("Enter a valid email address.", "danger")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
        elif password != confirm_password:
            flash("Passwords do not match.", "danger")
        else:
            try:
                db = get_db()
                db.execute(
                    """INSERT INTO users (full_name, username, email, password_hash)
                       VALUES (?, ?, ?, ?)""",
                    (full_name, username, email, generate_password_hash(password))
                )
                db.commit()
                flash("Account created successfully. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username or email is already registered.", "danger")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username_or_email = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username_or_email, username_or_email.lower())
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username/email or password.", "danger")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Welcome back, " + user["full_name"] + "!", "success")
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user = db.execute(
        """SELECT id, full_name, username, email, favorite_genres, bio, created_at
           FROM users WHERE id = ?""",
        (session["user_id"],)
    ).fetchone()
    if user is None:
        session.clear()
        flash("Your account could not be found. Please log in again.", "warning")
        return redirect(url_for("login"))

    movie_count = db.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    watched_count = db.execute(
        "SELECT COUNT(*) FROM watch_history WHERE user_id = ? AND status = 'Watched'",
        (session["user_id"],)
    ).fetchone()[0]
    watchlist_count = db.execute(
        "SELECT COUNT(*) FROM watch_history WHERE user_id = ? AND status = 'Want to Watch'",
        (session["user_id"],)
    ).fetchone()[0]
    return render_template(
        "dashboard.html", user=user, movie_count=movie_count,
        watched_count=watched_count, watchlist_count=watchlist_count
    )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    user = db.execute(
        "SELECT id, full_name, username, email, favorite_genres, bio FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        favorite_genres = request.form.get("favorite_genres", "").strip()
        bio = request.form.get("bio", "").strip()
        if not full_name:
            flash("Full name cannot be empty.", "danger")
        else:
            db.execute(
                """UPDATE users SET full_name = ?, favorite_genres = ?, bio = ?
                   WHERE id = ?""",
                (full_name, favorite_genres, bio, session["user_id"])
            )
            db.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for("profile"))

    user = db.execute(
        "SELECT id, full_name, username, email, favorite_genres, bio FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    return render_template("profile.html", user=user)


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------- Module 2: Catalog & History Management ----------------

@app.route("/movies")
@login_required
def movies():
    search = request.args.get("search", "").strip()
    genre = request.args.get("genre", "").strip()

    sql = "SELECT * FROM movies WHERE 1=1"
    params = []
    if search:
        sql += " AND (title LIKE ? OR director LIKE ? OR description LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
    if genre:
        sql += " AND genre LIKE ?"
        params.append(f"%{genre}%")
    sql += " ORDER BY title"

    db = get_db()
    movie_rows = db.execute(sql, params).fetchall()
    genre_rows = db.execute("SELECT DISTINCT genre FROM movies ORDER BY genre").fetchall()
    history_rows = db.execute(
        "SELECT movie_id, status FROM watch_history WHERE user_id = ?",
        (session["user_id"],)
    ).fetchall()
    user_status = {row["movie_id"]: row["status"] for row in history_rows}
    return render_template(
        "movies.html", movies=movie_rows, genres=genre_rows,
        selected_genre=genre, search=search, user_status=user_status
    )


@app.route("/movies/add", methods=["GET", "POST"])
@login_required
def add_movie():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        genre = request.form.get("genre", "").strip()
        year_text = request.form.get("release_year", "").strip()
        director = request.form.get("director", "").strip()
        description = request.form.get("description", "").strip()
        poster_url = request.form.get("poster_url", "").strip()

        if not title or not genre:
            flash("Movie title and genre are required.", "danger")
        else:
            try:
                year = int(year_text) if year_text else None
                if year is not None and (year < 1888 or year > 2100):
                    raise ValueError
                db = get_db()
                db.execute(
                    """INSERT INTO movies
                       (title, genre, release_year, director, description, poster_url)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (title, genre, year, director, description, poster_url)
                )
                db.commit()
                flash("Movie added to the catalog successfully.", "success")
                return redirect(url_for("movies"))
            except ValueError:
                flash("Enter a valid release year (1888–2100).", "danger")
    return render_template("add_movie.html")


@app.route("/movies/<int:movie_id>")
@login_required
def movie_detail(movie_id):
    db = get_db()
    movie = db.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if movie is None:
        flash("Movie not found.", "danger")
        return redirect(url_for("movies"))

    history = db.execute(
        """SELECT * FROM watch_history
           WHERE user_id = ? AND movie_id = ?""",
        (session["user_id"], movie_id)
    ).fetchone()
    rating_row = db.execute(
        "SELECT rating FROM ratings WHERE user_id = ? AND movie_id = ?",
        (session["user_id"], movie_id)
    ).fetchone()
    average_rating = db.execute(
        "SELECT AVG(rating) FROM ratings WHERE movie_id = ?", (movie_id,)
    ).fetchone()[0]
    rating_count = db.execute(
        "SELECT COUNT(*) FROM ratings WHERE movie_id = ?", (movie_id,)
    ).fetchone()[0]
    return render_template(
        "movie_detail.html", movie=movie, history=history,
        user_rating=rating_row["rating"] if rating_row else None,
        average_rating=average_rating, rating_count=rating_count
    )


@app.route("/history")
@login_required
def history():
    rows = get_db().execute(
        """SELECT m.*, h.id AS history_id, h.status, h.watched_on, h.added_at
           FROM watch_history h
           JOIN movies m ON m.id = h.movie_id
           WHERE h.user_id = ?
           ORDER BY h.added_at DESC""",
        (session["user_id"],)
    ).fetchall()
    return render_template("history.html", history=rows)


@app.route("/history/add/<int:movie_id>", methods=["POST"])
@login_required
def add_to_history(movie_id):
    db = get_db()
    movie = db.execute("SELECT id FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if movie is None:
        flash("Movie not found.", "danger")
        return redirect(url_for("movies"))

    try:
        db.execute(
            """INSERT INTO watch_history (user_id, movie_id, status)
               VALUES (?, ?, 'Want to Watch')""",
            (session["user_id"], movie_id)
        )
        db.commit()
        flash("Movie added to your watchlist.", "success")
    except sqlite3.IntegrityError:
        flash("This movie is already in your watchlist or history.", "info")
    return redirect(url_for("movie_detail", movie_id=movie_id))


@app.route("/history/status/<int:history_id>", methods=["POST"])
@login_required
def update_history_status(history_id):
    status = request.form.get("status", "")
    if status not in ("Want to Watch", "Watched"):
        flash("Invalid viewing status.", "danger")
        return redirect(url_for("history"))

    db = get_db()
    item = db.execute(
        "SELECT id FROM watch_history WHERE id = ? AND user_id = ?",
        (history_id, session["user_id"])
    ).fetchone()
    if item is None:
        flash("History item not found.", "danger")
    else:
        watched_on = request.form.get("watched_on", "").strip() if status == "Watched" else None
        db.execute(
            "UPDATE watch_history SET status = ?, watched_on = ? WHERE id = ? AND user_id = ?",
            (status, watched_on, history_id, session["user_id"])
        )
        db.commit()
        flash("Viewing history updated.", "success")
    return redirect(url_for("history"))


@app.route("/history/delete/<int:history_id>", methods=["POST"])
@login_required
def delete_history(history_id):
    db = get_db()
    db.execute(
        "DELETE FROM watch_history WHERE id = ? AND user_id = ?",
        (history_id, session["user_id"])
    )
    db.commit()
    flash("Movie removed from your watchlist/history.", "success")
    return redirect(url_for("history"))



# ---------------- Module 3: Machine Learning Recommendation Engine ----------------

def build_recommendations(user_id):
    """
    Hybrid recommender:
    1. Content-based similarity from genres, title and description using TF-IDF.
    2. Item-based collaborative filtering from the user-rating matrix.
    3. Profile genre preferences and viewing history are used as additional signals.

    The app still works if scikit-learn is not installed: a simple genre-overlap
    content score is used as a fallback.
    """
    db = get_db()
    user = db.execute(
        "SELECT favorite_genres FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    movie_rows = db.execute("SELECT * FROM movies ORDER BY title").fetchall()
    if not movie_rows:
        return [], []

    rating_rows = db.execute(
        "SELECT user_id, movie_id, rating FROM ratings"
    ).fetchall()
    my_ratings = {
        row["movie_id"]: row["rating"]
        for row in rating_rows if row["user_id"] == user_id
    }
    history_rows = db.execute(
        "SELECT movie_id, status FROM watch_history WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    history_ids = {row["movie_id"] for row in history_rows}
    excluded_ids = history_ids | set(my_ratings.keys())

    movies = [dict(row) for row in movie_rows]
    movie_by_id = {m["id"]: m for m in movies}
    profile_genres = (user["favorite_genres"] or "") if user else ""

    # Seed movies: highly rated movies and movies the user marked as watched.
    seed_ids = set()
    for movie_id, rating in my_ratings.items():
        if rating >= 3:
            seed_ids.add(movie_id)
    for row in history_rows:
        if row["status"] == "Watched":
            seed_ids.add(row["movie_id"])

    # Content-based scores using TF-IDF + cosine similarity.
    content_scores = {m["id"]: 0.0 for m in movies}
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        documents = [
            " ".join([
                m["title"] or "", m["genre"] or "",
                m["director"] or "", m["description"] or ""
            ])
            for m in movies
        ]
        profile_document = profile_genres
        for seed_id in seed_ids:
            seed = movie_by_id.get(seed_id)
            if seed:
                profile_document += " " + seed["genre"] + " " + seed["description"]
        corpus = documents + [profile_document or "movie entertainment"]
        matrix = TfidfVectorizer(stop_words="english").fit_transform(corpus)
        profile_vector = matrix[-1]
        similarities = cosine_similarity(profile_vector, matrix[:-1]).flatten()
        content_scores = {
            movies[i]["id"]: float(similarities[i])
            for i in range(len(movies))
        }
    except (ImportError, ValueError):
        preferred = {
            part.strip().lower()
            for part in profile_genres.split(",") if part.strip()
        }
        for movie in movies:
            genres = {part.strip().lower() for part in movie["genre"].split(",")}
            content_scores[movie["id"]] = (
                len(preferred & genres) / len(preferred | genres)
                if preferred | genres else 0.0
            )

    # Build item vectors: each movie is represented by ratings from all users.
    user_ids = sorted({row["user_id"] for row in rating_rows})
    movie_vectors = {}
    for row in rating_rows:
        movie_vectors.setdefault(row["movie_id"], {})
        movie_vectors[row["movie_id"]][row["user_id"]] = row["rating"]

    def cosine_dict(a, b):
        common = set(a) | set(b)
        dot = sum(a.get(uid, 0) * b.get(uid, 0) for uid in common)
        norm_a = sum(value * value for value in a.values()) ** 0.5
        norm_b = sum(value * value for value in b.values()) ** 0.5
        if not norm_a or not norm_b:
            return 0.0
        return dot / (norm_a * norm_b)

    collaborative_scores = {}
    for movie in movies:
        candidate_id = movie["id"]
        weighted_total = 0.0
        similarity_total = 0.0
        for seed_id, user_rating in my_ratings.items():
            if seed_id == candidate_id:
                continue
            similarity = cosine_dict(
                movie_vectors.get(candidate_id, {}),
                movie_vectors.get(seed_id, {})
            )
            if similarity > 0:
                weighted_total += similarity * user_rating
                similarity_total += similarity
        collaborative_scores[candidate_id] = (
            weighted_total / similarity_total if similarity_total else 0.0
        )

    # Global average rating and number of ratings for each movie.
    global_stats = {}
    for movie in movies:
        values = [
            row["rating"] for row in rating_rows
            if row["movie_id"] == movie["id"]
        ]
        global_stats[movie["id"]] = (
            (sum(values) / len(values), len(values)) if values else (0.0, 0)
        )

    recommendations = []
    for movie in movies:
        movie_id = movie["id"]
        if movie_id in excluded_ids:
            continue
        content_score = content_scores.get(movie_id, 0.0)
        cf_score = collaborative_scores.get(movie_id, 0.0)
        # Convert content similarity to a 1–5 scale. If there is no collaborative
        # data, content/profile similarity remains the principal signal.
        content_component = content_score * 5.0
        if cf_score > 0:
            hybrid_score = 0.65 * content_component + 0.35 * cf_score
            method = "Hybrid: content + collaborative"
        else:
            hybrid_score = content_component
            method = "Content-based"
        avg_rating, rating_count = global_stats[movie_id]
        movie_copy = dict(movie)
        movie_copy.update({
            "recommendation_score": round(hybrid_score, 2),
            "average_rating": round(avg_rating, 1) if rating_count else None,
            "rating_count": rating_count,
            "method": method
        })
        recommendations.append(movie_copy)

    recommendations.sort(
        key=lambda item: (item["recommendation_score"], item["average_rating"] or 0),
        reverse=True
    )

    top_rated = []
    for movie in movies:
        avg_rating, rating_count = global_stats[movie["id"]]
        if rating_count:
            movie_copy = dict(movie)
            movie_copy["average_rating"] = round(avg_rating, 1)
            movie_copy["rating_count"] = rating_count
            top_rated.append(movie_copy)
    top_rated.sort(
        key=lambda item: (item["average_rating"], item["rating_count"]),
        reverse=True
    )
    return recommendations[:8], top_rated[:8]


@app.route("/recommendations")
@login_required
def recommendations():
    recommended_movies, top_rated_movies = build_recommendations(session["user_id"])
    return render_template(
        "recommendations.html",
        recommendations=recommended_movies,
        top_rated=top_rated_movies
    )


@app.route("/ratings/<int:movie_id>", methods=["POST"])
@login_required
def save_rating(movie_id):
    db = get_db()
    movie = db.execute("SELECT id FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if movie is None:
        flash("Movie not found.", "danger")
        return redirect(url_for("movies"))

    try:
        rating = int(request.form.get("rating", ""))
    except (TypeError, ValueError):
        rating = 0

    if rating < 1 or rating > 5:
        flash("Please select a rating from 1 to 5 stars.", "danger")
        return redirect(url_for("movie_detail", movie_id=movie_id))

    db.execute("""
        INSERT INTO ratings (user_id, movie_id, rating)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, movie_id)
        DO UPDATE SET rating = excluded.rating,
                      updated_at = CURRENT_TIMESTAMP
    """, (session["user_id"], movie_id, rating))
    db.commit()
    flash("Your rating has been saved. Recommendations will use it.", "success")
    return redirect(url_for("movie_detail", movie_id=movie_id))


# ---------------- Module 4: Sentiment Analysis Service ----------------

def analyze_sentiment(review_text):
    """Analyze review polarity with VADER and return label plus score details."""
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    scores = SentimentIntensityAnalyzer().polarity_scores(review_text)
    compound = scores["compound"]
    if compound >= 0.05:
        label = "Positive"
    elif compound <= -0.05:
        label = "Negative"
    else:
        label = "Neutral"
    return label, scores


@app.route("/reviews")
@login_required
def reviews():
    db = get_db()
    movie_rows = db.execute("SELECT id, title FROM movies ORDER BY title").fetchall()
    review_rows = db.execute(
        """SELECT r.*, m.title AS movie_title, u.username
           FROM reviews r
           JOIN movies m ON m.id = r.movie_id
           JOIN users u ON u.id = r.user_id
           ORDER BY r.created_at DESC, r.id DESC LIMIT 50"""
    ).fetchall()
    summary_rows = db.execute(
        """SELECT sentiment, COUNT(*) AS total
           FROM reviews GROUP BY sentiment"""
    ).fetchall()
    sentiment_summary = {row["sentiment"]: row["total"] for row in summary_rows}
    total_reviews = sum(sentiment_summary.values())
    return render_template(
        "reviews.html", movies=movie_rows, reviews=review_rows,
        sentiment_summary=sentiment_summary, total_reviews=total_reviews
    )


@app.route("/reviews/add", methods=["POST"])
@login_required
def add_review():
    db = get_db()
    try:
        movie_id = int(request.form.get("movie_id", ""))
    except (TypeError, ValueError):
        movie_id = 0
    review_text = request.form.get("review_text", "").strip()

    movie = db.execute("SELECT id FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if movie is None:
        flash("Please select a valid movie.", "danger")
        return redirect(url_for("reviews"))
    if len(review_text) < 3:
        flash("Please write a review containing at least 3 characters.", "danger")
        return redirect(url_for("reviews"))
    if len(review_text) > 1000:
        flash("Your review must be 1000 characters or fewer.", "danger")
        return redirect(url_for("reviews"))

    try:
        sentiment, scores = analyze_sentiment(review_text)
    except ImportError:
        flash("Sentiment package is missing. Run: python -m pip install -r requirements.txt", "danger")
        return redirect(url_for("reviews"))

    db.execute(
        """INSERT INTO reviews
           (user_id, movie_id, review_text, sentiment, compound_score,
            positive_score, neutral_score, negative_score)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (session["user_id"], movie_id, review_text, sentiment, scores["compound"],
         scores["pos"], scores["neu"], scores["neg"])
    )
    db.commit()
    flash(f"Review submitted. Sentiment detected: {sentiment} ({scores['compound']:.2f}).", "success")
    return redirect(url_for("reviews"))


# ---------------- Module 5: Analytics Dashboard ----------------

@app.route("/analytics")
@login_required
def analytics():
    """Platform-wide statistics and charts for the analytics module."""
    db = get_db()

    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_movies = db.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    total_reviews = db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    total_ratings = db.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    total_watched = db.execute(
        "SELECT COUNT(*) FROM watch_history WHERE status = 'Watched'"
    ).fetchone()[0]
    total_watchlist = db.execute(
        "SELECT COUNT(*) FROM watch_history WHERE status = 'Want to Watch'"
    ).fetchone()[0]

    sentiment_rows = db.execute("""
        SELECT sentiment, COUNT(*) AS total
        FROM reviews
        GROUP BY sentiment
    """).fetchall()
    sentiment_counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for row in sentiment_rows:
        sentiment_counts[row["sentiment"]] = row["total"]

    # Most reviewed movies
    most_reviewed = db.execute("""
        SELECT m.id, m.title, COUNT(r.id) AS review_count
        FROM movies m
        LEFT JOIN reviews r ON r.movie_id = m.id
        GROUP BY m.id, m.title
        ORDER BY review_count DESC, m.title
        LIMIT 5
    """).fetchall()

    # Highest average ratings; show only movies with at least one rating
    top_rated = db.execute("""
        SELECT m.id, m.title, ROUND(AVG(rt.rating), 2) AS average_rating,
               COUNT(rt.id) AS rating_count
        FROM movies m
        JOIN ratings rt ON rt.movie_id = m.id
        GROUP BY m.id, m.title
        ORDER BY average_rating DESC, rating_count DESC, m.title
        LIMIT 5
    """).fetchall()

    # Most watched movies
    most_watched = db.execute("""
        SELECT m.id, m.title, COUNT(wh.id) AS watched_count
        FROM movies m
        LEFT JOIN watch_history wh
          ON wh.movie_id = m.id AND wh.status = 'Watched'
        GROUP BY m.id, m.title
        ORDER BY watched_count DESC, m.title
        LIMIT 5
    """).fetchall()

    max_review_count = max([row["review_count"] for row in most_reviewed] or [1])
    max_watched_count = max([row["watched_count"] for row in most_watched] or [1])
    max_rating = 5

    return render_template(
        "analytics.html",
        total_users=total_users,
        total_movies=total_movies,
        total_reviews=total_reviews,
        total_ratings=total_ratings,
        total_watched=total_watched,
        total_watchlist=total_watchlist,
        sentiment_counts=sentiment_counts,
        most_reviewed=most_reviewed,
        top_rated=top_rated,
        most_watched=most_watched,
        max_review_count=max_review_count,
        max_watched_count=max_watched_count,
        max_rating=max_rating
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
