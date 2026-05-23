# Percentage Error Practice — ErrCalc

An interactive web app to practice **percentage error calculations** using log
differentiation. Built with **Flask** (backend) + **Vanilla JS** (frontend).

## Features

- Enter any multiplicative equation (e.g. `V = l*b*h`, `P = I^2*R`)
- **Derivative Quiz** — fill in coefficients found via log differentiation
- Step-by-step **log differentiation hints** revealed one at a time
- Enter **percentage errors** for each variable
- **Answer Quiz** — calculate total % error and check it
- Step-by-step **calculation hints** if the answer is wrong
- Fully deployable to the web (Render, Railway, etc.)

---

## Project Structure

```
percentage_error_web/
├── app.py               # Flask API (7 endpoints)
├── requirements.txt
├── Procfile             # For Render / Railway
├── runtime.txt          # Python version
├── .gitignore
├── README.md
├── templates/
│   └── index.html       # Single-page app
└── static/
    ├── css/style.css
    └── js/app.js
```

---

## Local Development

```bash
# 1. Clone / navigate to the project folder
cd "d:/nikol/python project/percentage_error_web"

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the dev server
set FLASK_DEBUG=1              # Windows
# export FLASK_DEBUG=1         # macOS / Linux
python app.py
```

Open **http://localhost:5000** in your browser.

---

## Deploy to GitHub + Render (Free)

### Step 1 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/percentage-error-web.git
git push -u origin main
```

### Step 2 — Deploy on Render.com

1. Go to **https://render.com** and sign up / log in (free)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo
4. Fill in the settings:

| Field | Value |
|-------|-------|
| **Environment** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |
| **Instance Type** | Free |

5. Click **"Create Web Service"**
6. Render will build and give you a public URL like `https://your-app.onrender.com`

### Step 3 — Set a Secret Key (optional but recommended)

In Render's **Environment** tab, add:

| Key | Value |
|-----|-------|
| `SECRET_KEY` | `<any random long string>` |

---

## Supported Equation Examples

| Equation | Notes |
|----------|-------|
| `V = l*b*h` | Volume — all powers = 1 |
| `P = I^2 * R` | Power — I has power 2, R has power 1 |
| `E = m*c^2` | Energy — m has power 1, c has power 2 |
| `F = m*v^2/r` | Centripetal — m=1, v=2, r=−1 |
| `T = 2*pi*sqrt(l/g)` | Period — l=0.5, g=0.5 |

> **Tip:** Only multiplicative (product/power) expressions are supported.
> Equations with `+` or `−` on the right-hand side are not supported yet.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Serve the SPA |
| `POST` | `/api/parse` | Parse equation, detect variables & powers |
| `GET`  | `/api/deriv-hints` | Return log-diff hint steps |
| `POST` | `/api/check-deriv` | Check user's derivative coefficients |
| `POST` | `/api/set-errors` | Accept % errors, compute answer |
| `POST` | `/api/check-answer` | Verify user's total % error |
| `GET`  | `/api/calc-hints` | Return calculation hint steps |

---

## Tech Stack

- **Backend:** Python 3.11, Flask 3, SymPy 1.12, Gunicorn
- **Frontend:** Vanilla HTML5 / CSS3 / JavaScript (no framework)
- **Fonts:** Inter + JetBrains Mono (Google Fonts)
