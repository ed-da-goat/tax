# Environment Setup Guide — Georgia CPA Firm Accounting System

**Tech stack:** Python 3.11+ (FastAPI), Node.js 18+ (React + Vite), PostgreSQL 15+, WeasyPrint

**Platform:** macOS

---

## 1. Install Homebrew

If you do not already have Homebrew installed, run this in Terminal:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen prompts. When it finishes, it may tell you to run additional commands to add Homebrew to your PATH. Run those commands exactly as shown.

**VERIFY:**

```bash
brew --version
```

You should see a version number like `Homebrew 4.x.x`.

---

## 2. Install Python 3.11+

```bash
brew install python@3.11
```

**VERIFY:**

```bash
python3 --version
```

You should see `Python 3.11.x` or higher. If you see an older version, run `brew link python@3.11` and try again.

---

## 3. Install Node.js 18+

```bash
brew install node@18
```

If Homebrew tells you the keg is not linked, run:

```bash
brew link node@18
```

**VERIFY:**

```bash
node --version && npm --version
```

You should see `v18.x.x` (or higher) for Node and a version number for npm.

---

## 4. Install and Configure PostgreSQL 15

### 4a. Install PostgreSQL

```bash
brew install postgresql@15
```

### 4b. Start the PostgreSQL service

```bash
brew services start postgresql@15
```

### 4c. Create the database and user

Open a PostgreSQL shell:

```bash
psql postgres
```

Inside the shell, run these commands one at a time:

```sql
CREATE USER cpa_admin WITH PASSWORD 'changeme_in_production';
CREATE DATABASE cpa_accounting OWNER cpa_admin;
GRANT ALL PRIVILEGES ON DATABASE cpa_accounting TO cpa_admin;
\q
```

Change `changeme_in_production` to a strong password before deploying to any real environment.

**VERIFY:**

```bash
psql -U cpa_admin -d cpa_accounting -c "SELECT 1;"
```

You should see a table with a single row containing `1`. If you get a peer authentication error, you may need to edit your `pg_hba.conf` to allow password authentication for local connections (Homebrew typically handles this automatically).

---

## 5. Clone the Repository

Replace `your-org` with the actual GitHub organization or username:

```bash
cd ~
git clone https://github.com/your-org/cpa-accounting.git
cd cpa-accounting
```

**VERIFY:**

```bash
ls -la
```

You should see project files including `requirements.txt`, a `frontend/` directory, and a `db/` directory.

---

## 6. Set Up the Python Backend

### 6a. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

Your terminal prompt should now start with `(venv)`.

### 6b. Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, WeasyPrint, and all other backend dependencies. WeasyPrint requires some system libraries. If the install fails on WeasyPrint, run:

```bash
brew install pango gdk-pixbuf libffi
pip install -r requirements.txt
```

**VERIFY:**

```bash
python -c "import fastapi; print('FastAPI OK')"
```

You should see `FastAPI OK` printed with no errors.

---

## 7. Set Up the Frontend

```bash
cd frontend
npm install
```

**VERIFY:**

```bash
npm run dev
```

Vite should start and print a local URL like `http://localhost:5173`. Press `Ctrl+C` to stop it once you confirm it works.

```bash
cd ..
```

---

## 8. Run Database Migrations

Make sure you are back in the project root directory.

```bash
psql -U cpa_admin -d cpa_accounting -f db/migrations/001_initial_schema.sql
```

**VERIFY:**

```bash
psql -U cpa_admin -d cpa_accounting -c "\dt"
```

You should see a list of tables created by the migration script (e.g., `clients`, `invoices`, `transactions`, etc.).

---

## 9. Create the .env File

From the project root, create a `.env` file:

```bash
cat > .env << 'EOF'
DATABASE_URL=postgresql://cpa_admin:changeme_in_production@localhost:5432/cpa_accounting
JWT_SECRET=replace_with_a_random_secret_string
ENVIRONMENT=development
EOF
```

Then update the two placeholder values:

- **DATABASE_URL** — replace `changeme_in_production` with the password you set in step 4c.
- **JWT_SECRET** — replace with a long random string. You can generate one with:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as the value for `JWT_SECRET`.

**VERIFY:**

```bash
cat .env
```

Confirm the file exists and has your actual values filled in. Do not commit this file to version control.

---

## 10. Start the Dev Servers

You need two terminal windows (or tabs).

### Terminal 1 — Backend

From the project root, with the virtual environment activated:

```bash
source venv/bin/activate
uvicorn backend.app.main:app --reload
```

The API should start at `http://localhost:8000`. You can check the auto-generated docs at `http://localhost:8000/docs`.

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

The frontend should start at `http://localhost:5173`.

---

## Quick Reference

| Service    | URL                          |
|------------|------------------------------|
| Backend API | http://localhost:8000       |
| API Docs    | http://localhost:8000/docs  |
| Frontend    | http://localhost:5173       |

To stop either server, press `Ctrl+C` in its terminal window.
