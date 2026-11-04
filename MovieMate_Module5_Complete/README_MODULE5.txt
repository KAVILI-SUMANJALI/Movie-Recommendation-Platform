MOVIEMATE - MODULE 5: ANALYTICS DASHBOARD
==========================================

This folder contains the integrated MovieMate project (Modules 1 to 5).

MODULE 5 FEATURES
- Registered user count
- Movie catalog count
- Total reviews and ratings
- Watched and watchlist counts
- Positive, Negative and Neutral sentiment distribution
- Most reviewed movies
- Most watched movies
- Top rated movies

INSTALLATION
1. Extract this ZIP.
2. IMPORTANT: Copy your existing movie_platform.db from your working Module 4 folder
   into this project folder. Back up the database before copying.
3. Open PowerShell in the folder containing app.py and requirements.txt.
4. Run: python -m pip install -r requirements.txt
5. Run: python app.py
6. Open: http://127.0.0.1:5000
7. Log in and click Analytics Dashboard in the navigation bar.

DATABASE SAFETY
The app uses CREATE TABLE IF NOT EXISTS and does not delete existing tables.
Copy your existing movie_platform.db into this folder to retain your users,
movies, watch history, ratings and reviews. Do not replace your old database
with a newly-created empty database.

The dashboard is available to logged-in users and displays aggregate platform
statistics. Empty charts are normal until users add reviews, ratings or history.
