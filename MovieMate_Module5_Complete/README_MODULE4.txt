MOVIEMATE — MODULE 4: SENTIMENT ANALYSIS

This version includes Modules 1, 2, 3 and 4. Module 4 uses VADER sentiment analysis to classify user movie reviews as Positive, Negative or Neutral. It saves the review and sentiment scores in SQLite.

IMPORTANT — PRESERVE YOUR EXISTING DATA
Before using this folder, copy your existing movie_platform.db from your working Module 3 project folder into this folder. If Windows asks whether to replace the database included in the project, keep your existing database / choose Replace only after making a backup. The ZIP intentionally does not include a database file, so your existing accounts, movies, ratings and watch history can be preserved.

INSTALL
Open PowerShell in the folder containing app.py and run:
python -m pip install -r requirements.txt

RUN
python app.py

Open http://127.0.0.1:5000, log in, and click “Reviews & Sentiment” in the navigation bar. Select a movie, write a review and click “Analyze & Submit Review”.

SENTIMENT RULES
VADER returns a compound score from -1 to +1. Compound >= 0.05 is Positive; <= -0.05 is Negative; values between them are Neutral.

DATABASE
On startup, CREATE TABLE IF NOT EXISTS creates the reviews table. Existing users, movies, watch history and ratings are not dropped or overwritten.
