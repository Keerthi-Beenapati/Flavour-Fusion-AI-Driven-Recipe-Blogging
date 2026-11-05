# Flavour Fusion — Professional AI Recipe Studio

A complete Flask + SQLite recipe discovery and blogging application upgraded from the supplied prototype. It includes recipe search/filtering, recipe detail pages, account registration/sign-in, publishing recipes, saved favourites, meal planning, and an ingredient-based recipe drafting page. The recipe drafting page works locally without an API key and can optionally use Google's Gemini API.

## Requirements
- Python 3.10+
- Windows, macOS, or Linux
- Internet connection only for loading remote Unsplash imagery / installing packages

## Run on Windows
1. Extract the ZIP.
2. Open the extracted `FlavourFusion_Professional` folder in VS Code.
3. Open Terminal in that folder.
4. Create a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.
5. Install dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
6. Start the app:
   ```powershell
   python app.py
   ```
7. Open `http://127.0.0.1:5000` in your browser.

The SQLite database is created automatically on first run and seeded with sample recipes. No manual database setup is required.

## Enable Gemini recipe generation (optional)
1. Install the optional provider package:
   `pip install google-generativeai`
2. Create an API key in Google's AI developer console.
3. Set the environment variable in the same terminal before starting the app:
   ```powershell
   $env:GEMINI_API_KEY="your-key-here"
   python app.py
   ```
Do not paste API keys into source code or commit them to GitHub. Without a key, the ingredient recipe drafting feature still works using a local fallback.

## Features
- Responsive recipe library with text search and filters for cuisine, diet and cooking time.
- Individual recipe pages with ingredients and instructions.
- Register/sign in with hashed passwords.
- Publish community recipes.
- Save and remove favourites.
- Personal meal planner with dates and meal types.
- Ingredient-based recipe drafting with optional Gemini integration.
- SQLite persistence; data remains after app restarts.
- Input validation, parameterized SQL queries, session-based authentication, and helpful error pages.

## Important production notes
This is a local-development-ready academic project, not a deployed production service. Before public deployment, set a strong `FLAVOUR_FUSION_SECRET`, disable debug mode, use HTTPS, configure CSRF protection and rate limiting, add database backups and migrations, and review privacy/security requirements. The starter sample recipes and local fallback are demonstration content; AI drafts should be reviewed for food safety and dietary needs.
