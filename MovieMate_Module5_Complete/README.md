# MovieMate — Movie Recommendation Platform (Modules 1–4)

This project contains:
- Module 1: Authentication & Profile Management
- Module 2: Movie Catalog & Viewing History
- Module 3: Hybrid Recommendation Engine and movie ratings
- Module 4: Sentiment Analysis Service for movie reviews

## Requirements
Python 3.9 or later.

## Install packages
Open PowerShell in the folder containing `app.py` and run:

```powershell
python -m pip install -r requirements.txt
```

## Run the application

```powershell
python app.py
```

Open `http://127.0.0.1:5000` in your browser and sign in.

## Module 4: Reviews & Sentiment
1. Click **Reviews & Sentiment** in the navigation bar.
2. Select a movie.
3. Write a review of 3–1000 characters.
4. Click **Analyze & Submit Review**.
5. The application classifies the review as Positive, Negative or Neutral and saves the review and sentiment scores in SQLite.

VADER compound-score thresholds:
- Positive: compound score >= 0.05
- Negative: compound score <= -0.05
- Neutral: between -0.05 and 0.05

## Database preservation
The ZIP does not include a database file. Before running this version, copy your existing `movie_platform.db` from your working Module 3 folder into this folder. This keeps your registered accounts, movies, watch history and ratings. Make a backup copy first. On startup, the app creates the new `reviews` table with `CREATE TABLE IF NOT EXISTS`; it does not delete existing tables or records.

If you do not copy your old database, the app creates a new database and you will need to register again.
