# Board Prep Intel — Website Build Guide
## "How to Deploy This Thing" for People Who Have Never Built a Website

> **Who this is for:** You know Python, you can run a terminal command, you've worked with API keys and SQLite — but you've never deployed a web app. This guide explains everything from scratch, including what each technology IS before telling you how to use it.

---

## Table of Contents

1. [What Are We Building?](#1-what-are-we-building)
2. [The Tech Stack, Decoded](#2-the-tech-stack-decoded)
3. [Before You Start: Ingredients](#3-before-you-start-ingredients)
4. [Phase 1 — Supabase: Your Cloud Database](#4-phase-1--supabase-your-cloud-database)
5. [Phase 2 — Sync Your Data to Supabase](#5-phase-2--sync-your-data-to-supabase)
6. [Phase 3 — Railway: The Python Worker](#6-phase-3--railway-the-python-worker)
7. [Phase 4 — Sanity: The Curriculum CMS](#7-phase-4--sanity-the-curriculum-cms)
8. [Phase 5 — Run It Locally First](#8-phase-5--run-it-locally-first)
9. [Phase 6 — Netlify: Deploy to the Internet](#9-phase-6--netlify-deploy-to-the-internet)
10. [Phase 7 — Custom Domain (slbfm.com)](#10-phase-7--custom-domain-slbfmcom)
11. [Phase 8 — Add Your First Users](#11-phase-8--add-your-first-users)
12. [Troubleshooting](#12-troubleshooting)
13. [Day-to-Day: After It's Live](#13-day-to-day-after-its-live)

---

## 1. What Are We Building?

Think of this as a **private resident education portal** that lives at `slbfm.com`. It has three types of users:

| User type | What they do on the site |
|-----------|--------------------------|
| **Resident** | Takes practice exams, uploads their ABFM ITE score report PDF, views analytics showing their weak areas, reads assigned articles |
| **Faculty** (you) | Searches the question/article database using plain English ("give me 15 questions on abdominal pain"), saves question sets, assigns them to residents, manages the curriculum |
| **Admin** | Manages user accounts, monitors the DB sync status |

The data that powers all of this already exists in your SQLite database (`ite_intelligence.db`). The website just puts a front door on it.

**The short version of how the pieces connect:**

```
Your computer (SQLite DB)
        │
        ▼ (one-time sync, then re-run after pipeline updates)
   Supabase (cloud PostgreSQL)  ←──── website reads/writes here
        │
        ▼
   Netlify (hosts the website at slbfm.com)
        │
        ├── Faculty search → OpenAI API (for NL query embedding)
        └── Resident score upload → Railway (Python PDF parser)
```

**Sanity** is a separate content management tool — it's where you'll create curriculum sessions, assign question sets to residents, and write announcements. Think of it as a specialized admin panel just for curriculum management.

---

## 2. The Tech Stack, Decoded

### Next.js
A framework for building websites in JavaScript/TypeScript. It handles routing (what URL shows what page), server-side logic, and the build/deploy process. You do not need to write JavaScript — it's already written. You just need to **run it** and **configure it**.

### Netlify
A hosting service. When you run `npm run build` in the frontend folder, it produces a bundle of files. Netlify takes those files and serves them to the world at your domain. Netlify also re-runs the build automatically every time you push a commit to GitHub. Think of it as: Netlify = the web server you don't have to manage.

### Supabase
A managed PostgreSQL (full-featured relational database) in the cloud, plus:
- **Authentication** — login/logout, user management
- **Row Level Security (RLS)** — residents can only see their own scores, not others'
- **Storage** — file upload storage (where residents' PDF score reports go)
- **pgvector** — the vector similarity search extension (same concept as sqlite-vec, but in the cloud)

Your SQLite database is the source of truth. Supabase is the cloud mirror that the website reads from. You sync data from SQLite → Supabase using the scripts already in `supabase/sync/`.

### Sanity
A headless CMS (Content Management System). You use it to create and manage curriculum content: sessions, reading assignments, assessment assignments, announcements. The website reads from Sanity to know "what should Resident X see this week." You do not store question data in Sanity — it just stores references (like "this assignment uses QID-2024-0042 through QID-2024-0060").

### Railway
A cloud platform for running Python (and other) services. The PDF score report parser (`ite_parser.py`) is a Python script — it can't run inside Netlify. Railway hosts it as a microservice. When a resident uploads their ITE PDF, the website calls Railway to do the parsing and write the results back to Supabase.

### OpenAI API
You already have an OpenAI API key from the enrichment pipeline. The website uses the same `text-embedding-3-small` model to convert faculty search queries ("abdominal pain questions") into vectors, then finds the most similar question vectors in Supabase. This runs entirely server-side — the key is never exposed to the browser.

---

## 3. Before You Start: Ingredients

### Accounts to Create (do this first, before anything else)

| Service | URL | Free tier? | Notes |
|---------|-----|-----------|-------|
| **Supabase** | https://supabase.com | Yes (generous) | Free tier handles this workload |
| **Netlify** | https://netlify.com | Yes | Free tier works for private programs |
| **Sanity** | https://sanity.io | Yes | Free for small projects |
| **Railway** | https://railway.app | $5/month starter | Needed for the Python parser |
| **GitHub** | https://github.com | Free | You already have this |

Sign up for all five. For each one, use the same email address and use Google sign-in where offered — it simplifies password management.

### API Keys to Gather

Before Phase 5, you'll need these keys. Gather them as you complete each Phase:

| Key | Where to find it | When you need it |
|-----|-----------------|-----------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase → Settings → API | Phase 5 |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase → Settings → API | Phase 5 |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API | Phase 5 |
| `SUPABASE_DB_URL` | Supabase → Settings → Database → Connection string | Phase 2 |
| `NEXT_PUBLIC_SANITY_PROJECT_ID` | Sanity CLI output after `sanity init` | Phase 5 |
| `NEXT_PUBLIC_SANITY_DATASET` | `production` (default) | Phase 5 |
| `OPENAI_API_KEY` | You already have this | Phase 5 |
| `SCORE_PARSER_API_URL` | Railway → your app URL after deploy | Phase 5 |
| `SCORE_PARSER_API_SECRET` | You pick this (any random string) | Phase 3 + 5 |

### Software to Install on Your Mac

You likely already have most of this. Check each one:

**Node.js** (required for Next.js and Sanity):
```bash
node --version
```
If you get a version number (e.g., `v20.x.x`), you're set. If not:
1. Go to https://nodejs.org
2. Download the **LTS** version (the one labeled "Recommended for most users")
3. Run the installer — it installs both `node` and `npm`

Verify afterward:
```bash
node --version   # should show v20 or higher
npm --version    # should show 10 or higher
```

**Python** (already have this) — confirm:
```bash
python --version   # or python3 --version
```

**pip packages for the sync scripts** — install once:
```bash
pip install supabase python-dotenv tqdm psycopg2-binary
```

---

## 4. Phase 1 — Supabase: Your Cloud Database

### Step 1.1: Create a Supabase Project

1. Go to https://supabase.com and sign in
2. Click **"New project"**
3. Fill in:
   - **Organization:** Create one (your name or "SLBFM")
   - **Name:** `board-prep-intel`
   - **Database Password:** Click "Generate a password", save it somewhere (you'll need it in Step 1.4)
   - **Region:** Choose `US East (N. Virginia)` or closest to you
4. Click **"Create new project"**
5. Wait 2–3 minutes. You'll see a loading screen. When it finishes you'll land on the project dashboard.

### Step 1.2: Enable the pgvector Extension

The vector search feature requires a PostgreSQL extension called `pgvector`. Enable it:

1. In your Supabase project, click **"SQL Editor"** in the left sidebar
2. Click **"New query"**
3. Paste this and click **"Run"**:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. You should see: `Success. No rows returned`

### Step 1.3: Run the Database Migrations

Migrations are SQL scripts that create your tables. Run them in order (001 → 005). Each one builds on the last — **do not skip or reorder them**.

For each migration file:
1. In the SQL Editor, click **"New query"**
2. Open the migration file in your text editor (they're in `05_module.5_web/supabase/migrations/`)
3. Select all text, copy it
4. Paste it into the SQL Editor
5. Click **"Run"**
6. Confirm you see `Success` (not an error)

Run them in this order:
| File | What it creates |
|------|----------------|
| `001_core_schema.sql` | `articles`, `questions`, `qid_art_xref`, `aafp_questions`, ICD-10 tables |
| `002_vector_tables.sql` | Vector tables + pgvector similarity search functions |
| `003_resident_tables.sql` | `user_profiles`, `resident_scores`, `score_uploads`, `question_sets` |
| `004_rls_policies.sql` | Row Level Security — residents can only see their own data |
| `005_functions.sql` | Analytics helper functions (aggregation queries for the dashboard) |

> **What is RLS?** Row Level Security means the database itself enforces data isolation — even if a bug in the website code tries to fetch all residents' scores, the database will refuse unless the request is authenticated as an admin. It's a safety net built into Supabase.

### Step 1.4: Get Your Credentials

1. In Supabase, click **"Settings"** (gear icon in left sidebar)
2. Click **"API"**
3. Copy and save these three values somewhere safe (a text file is fine — you'll use them as env vars):
   - **Project URL** — looks like `https://abcdefghij.supabase.co` → this is `NEXT_PUBLIC_SUPABASE_URL`
   - **anon public** key → this is `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - **service_role secret** key → this is `SUPABASE_SERVICE_ROLE_KEY`

4. Now click **"Database"** in the settings sidebar
5. Under **"Connection string"**, choose the **"URI"** tab
6. Copy that string — it looks like:
   `postgresql://postgres.abcdefghij:[YOUR_PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres`
   Replace `[YOUR_PASSWORD]` with the password you saved in Step 1.1
   → This is `SUPABASE_DB_URL`

### Step 1.5: Enable Supabase Storage

1. Click **"Storage"** in the left sidebar
2. Click **"New bucket"**
3. Name it: `score-reports`
4. Leave it set to **Private** (NOT public — these are patient-adjacent documents)
5. Click **"Create bucket"**

---

## 5. Phase 2 — Sync Your Data to Supabase

This transfers your SQLite database to Supabase. You'll run this from your Mac (where the SQLite file lives), not from the server.

### Step 2.1: Set Up Environment Variables

The sync scripts need your Supabase credentials. Create a `.env` file at the repo root (the same level as `README.md`):

```bash
# In the board_prep_intel directory:
nano .env
```

Add these lines (replace the placeholder values):
```
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGc...your_service_role_key...
SUPABASE_DB_URL=postgresql://postgres.YOUR_REF:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

Save and close (`Ctrl+O`, `Enter`, `Ctrl+X` in nano; or just save normally if using another editor).

> **Why is it called SUPABASE_SERVICE_KEY here vs. SUPABASE_SERVICE_ROLE_KEY in the frontend?** The sync scripts were written before the frontend naming was standardized. Both names refer to the same key — the service_role key from Supabase Settings → API. Both scripts and the frontend load from their respective places; just make sure both have it.

### Step 2.2: Run the Content Sync

```bash
cd /path/to/board_prep_intel

python 05_module.5_web/supabase/sync/sqlite_to_supabase.py
```

This copies all articles, questions, xref tables, ICD-10 mappings, pathways, and article_currency to Supabase. Expected runtime: 5–15 minutes depending on your internet speed. You'll see a progress bar for each table.

Expected output looks like:
```
Syncing articles... ████████████████ 1985/1985 [00:23]
Syncing questions... ████████████████ 1629/1629 [00:18]
...
Sync complete.
```

> **If you get an error like "relation does not exist":** You skipped or failed a migration step. Go back to Phase 1, Step 1.3, and check which migration didn't complete successfully.

### Step 2.3: Run the Vector Sync

This copies the embedding vectors (used for NL search). It requires a direct PostgreSQL connection (the `SUPABASE_DB_URL` you set above):

```bash
python 05_module.5_web/supabase/sync/vector_sync.py
```

Expected runtime: 10–20 minutes. Output shows progress per vector table.

### Step 2.4: Validate NL Search

Before building the UI, confirm the vectors are loaded and working:

```bash
export OPENAI_API_KEY=sk-your-openai-key

python 04_module.4_sandbox/scripts/nl_search_validation.py "abdominal pain acute and chronic" --count 15
```

You should see 15 questions ranked by relevance printed to the terminal. If you see results, **the database is ready** and you can move on.

> **If you get zero results:** The vector sync may not have completed, or pgvector wasn't enabled before running `002_vector_tables.sql`. Check Supabase → SQL Editor and run:
> ```sql
> SELECT COUNT(*) FROM question_icd10_vec;
> ```
> If that returns 0, re-run the vector sync.

---

## 6. Phase 3 — Railway: The Python Worker

This deploys the PDF score parser as a cloud service. The parser is written in Python and needs to run on a server that can execute Python — Netlify can't do that (it only hosts the JavaScript frontend).

### Step 3.1: Prepare the Parser Files

Before deploying, you need to copy the parser source files into the API directory:

```bash
cd /path/to/board_prep_intel

cp 03_module.3_analyst/scripts/ite_parser.py 05_module.5_web/api/parser/
cp 03_module.3_analyst/scripts/ite_parser_config.json 05_module.5_web/api/parser/
```

> **Why isn't this done automatically?** The `api/parser/` directory is intentionally empty in the repo — the parser script is maintained in M3 (the analyst module) and is just copied here for deployment. This keeps the source of truth in one place.

### Step 3.2: Create a Railway Project

1. Go to https://railway.app and sign in
2. Click **"New Project"**
3. Choose **"Deploy from GitHub repo"**
4. Authorize Railway to access your GitHub account if prompted
5. Select `mpsch01/board_prep_intel`
6. Railway will detect it as a Python/Node project — that's fine

### Step 3.3: Configure the Railway Service

Railway may try to auto-deploy everything. You only want it to deploy the `api/` subdirectory:

1. Click on your new service in the Railway dashboard
2. Click **"Settings"** tab
3. Under **"Source"**, set **"Root Directory"** to: `05_module.5_web/api`
4. Under **"Deploy"**, the start command should already be set (from `railway.json`):
   `uvicorn main:app --host 0.0.0.0 --port $PORT`
   If it's not, set it manually.
5. Click **"Save"**

### Step 3.4: Set Environment Variables in Railway

1. In your Railway service, click **"Variables"** tab
2. Add these three variables (click **"+ New Variable"** for each):
   - `SUPABASE_URL` = your Supabase project URL
   - `SUPABASE_SERVICE_KEY` = your Supabase service_role key
   - `PARSER_SECRET` = pick any long random string (e.g., open Terminal and run `python3 -c "import secrets; print(secrets.token_hex(32))"` — copy the output). **Save this value — you'll need it again in Phase 5.**
   - `ENV` = `production`

3. Click **"Deploy"** (Railway may do this automatically after you save vars)

### Step 3.5: Get Your Railway URL

1. Once deployed (2–3 minutes), click the **"Deployments"** tab
2. Click on the latest deployment
3. You'll see a URL like `https://board-prep-intel-api-production.up.railway.app`
4. Save this as `SCORE_PARSER_API_URL`

### Step 3.6: Test It

Open a browser and go to:
```
https://YOUR_RAILWAY_URL.railway.app/health
```

You should see:
```json
{"status": "ok"}
```

If you see that, the API is live. If you see an error, check Railway → Deployments → Logs to diagnose.

---

## 7. Phase 4 — Sanity: The Curriculum CMS

Sanity is where you'll manage curriculum content. It runs as a "studio" (a web app) that you can embed in the faculty admin panel of your site, or access directly.

### Step 4.1: Install and Initialize

```bash
cd /path/to/board_prep_intel/05_module.5_web/sanity

npm install
```

This installs Sanity's dependencies (you'll see a `node_modules` folder appear — normal, and gitignored).

Now initialize your Sanity project:
```bash
npx sanity init
```

You'll be prompted with several questions:
- **"Create new project or use existing?"** → Create new project
- **"Project name"** → `Board Prep Intel Curriculum`
- **"Dataset"** → press Enter to accept `production`
- **"Output path"** → press Enter to accept current directory

When it finishes, it will print your **Project ID** — save this as `NEXT_PUBLIC_SANITY_PROJECT_ID`.

### Step 4.2: Run the Studio Locally

```bash
npm run dev
```

This starts the Sanity Studio at http://localhost:3333. Open it in your browser. You'll see an empty CMS with schemas for:
- **Resident Cohorts** — groups of residents (e.g., "PGY-2 Class of 2026")
- **Curriculum Sessions** — the 48 VC sessions
- **Prescribed Readings** — article assignments linked to article_ids
- **Assessment Assignments** — question set assignments (QID ranges or saved sets)
- **Faculty Announcements** — program announcements

You don't need to create any content yet — just confirm the studio loads without errors. You can create a test cohort to make sure everything is working.

### Step 4.3: Deploy the Studio

Later, when you deploy the full website, the Sanity Studio will be embedded in the faculty admin panel at `/faculty/curriculum`. For now, running it locally is sufficient for testing.

---

## 8. Phase 5 — Run It Locally First

**Always run locally before deploying to the internet.** This is the "does it work at all?" check.

### Step 5.1: Install Frontend Dependencies

```bash
cd /path/to/board_prep_intel/05_module.5_web/frontend

npm install
```

This downloads all the JavaScript libraries listed in `package.json`. The `node_modules` folder will be ~500MB — that's normal and gitignored.

### Step 5.2: Create Your Local Environment File

```bash
cp .env.example .env.local
```

Now open `.env.local` in a text editor and fill in all the values you've collected:

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...your_anon_key...

# Sanity CMS
NEXT_PUBLIC_SANITY_PROJECT_ID=YOUR_SANITY_PROJECT_ID
NEXT_PUBLIC_SANITY_DATASET=production

# OpenAI (server-side only)
OPENAI_API_KEY=sk-your-openai-key

# Railway Python API
SCORE_PARSER_API_URL=https://YOUR_RAILWAY_APP.railway.app
SCORE_PARSER_API_SECRET=the-same-secret-you-set-in-railway

# Supabase service_role (server-side only — NOT NEXT_PUBLIC)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...your_service_role_key...
```

> **IMPORTANT — Two types of env vars:**
> - `NEXT_PUBLIC_*` variables are **visible to the browser**. Only put non-sensitive keys here (the anon key, Sanity project ID, Supabase URL).
> - Variables **without** `NEXT_PUBLIC_` are server-only. The OpenAI key and Supabase service_role key must never be in a `NEXT_PUBLIC_*` variable.

### Step 5.3: Start the Dev Server

```bash
npm run dev
```

You'll see output like:
```
▲ Next.js 15.2.4
- Local:        http://localhost:3000
- Network:      http://192.168.1.x:3000

✓ Ready in 2.1s
```

Open http://localhost:3000 in your browser.

### Step 5.4: What You Should See

The page will redirect you to `/login` since you're not authenticated.

> **You don't have a login yet!** You'll create the first user (yourself, as admin) in Phase 8. For now, just confirm the login page loads without JavaScript errors. Open DevTools (Cmd+Option+I) → Console tab — there should be no red errors.

To fully test the app locally you'll need at least one user in Supabase Authentication. Jump ahead to Phase 8, Step 8.1 to create yourself as admin, then come back and log in at http://localhost:3000/login.

---

## 9. Phase 6 — Netlify: Deploy to the Internet

Once it works locally, deploying to Netlify takes about 10 minutes.

### Step 6.1: Connect Your Repo

1. Go to https://netlify.com and sign in
2. Click **"Add new site"** → **"Import an existing project"**
3. Click **"Deploy with GitHub"**
4. Authorize Netlify to access your GitHub if prompted
5. Select `mpsch01/board_prep_intel`

### Step 6.2: Configure the Build

Netlify will show you build settings. Fill them in:

| Setting | Value |
|---------|-------|
| **Branch to deploy** | `main` |
| **Base directory** | `05_module.5_web/frontend` |
| **Build command** | `npm run build` |
| **Publish directory** | `05_module.5_web/frontend/.next` |

> **Why base directory?** Your repo contains the whole `board_prep_intel` project — not just the website. Netlify needs to know to only build the `frontend` subfolder.

### Step 6.3: Add Environment Variables

Before deploying, add your environment variables:

1. Click **"Advanced"** (below the build settings)
2. Click **"New variable"** for each one — add ALL the same variables from your `.env.local` file:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_SANITY_PROJECT_ID`
   - `NEXT_PUBLIC_SANITY_DATASET`
   - `OPENAI_API_KEY`
   - `SCORE_PARSER_API_URL`
   - `SCORE_PARSER_API_SECRET`
   - `SUPABASE_SERVICE_ROLE_KEY`

3. Click **"Deploy site"**

### Step 6.4: Watch the Build

Netlify will show a build log in real time. The first build takes 3–5 minutes. A successful build ends with:
```
✓ Finished
Site is live ✓
```

If it fails, scroll up in the build log to find the first error (not the last). Common issues:
- Missing environment variable → check Step 6.3
- TypeScript error → see Troubleshooting section

### Step 6.5: Test Your Live Site

Netlify gives you a temporary URL like `https://amazing-giraffe-abc123.netlify.app`. Open it — you should see the same login page you saw locally.

---

## 10. Phase 7 — Custom Domain (slbfm.com)

### Step 7.1: Add the Domain in Netlify

1. In your Netlify site, click **"Site configuration"** → **"Domain management"**
2. Click **"Add custom domain"**
3. Enter: `slbfm.com`
4. Click **"Verify"** → Netlify will say the domain isn't pointing to Netlify yet — that's expected

Also add `www.slbfm.com` as an alias and set `slbfm.com` as the primary domain.

### Step 7.2: Update Your DNS Records

Log in to wherever you registered `slbfm.com` (likely Google Domains, Squarespace Domains, or GoDaddy). You need to add a DNS record that points `slbfm.com` → Netlify.

**The simplest method — change nameservers to Netlify (recommended):**

1. In Netlify → Domain management, you'll see Netlify's nameservers listed. They look like:
   ```
   dns1.p01.nsone.net
   dns2.p01.nsone.net
   dns3.p01.nsone.net
   dns4.p01.nsone.net
   ```
2. In your domain registrar, find **"Nameservers"** or **"DNS Settings"**
3. Change the nameservers to Netlify's four nameservers
4. Save

DNS changes take 5 minutes to 48 hours to propagate. Netlify's dashboard will turn the domain green when it detects the connection.

### Step 7.3: Enable HTTPS

Once DNS is pointed correctly, Netlify automatically provisions a free SSL certificate (HTTPS) via Let's Encrypt. This usually happens within minutes of DNS propagating. You'll see a green padlock on https://slbfm.com when it's done.

---

## 11. Phase 8 — Add Your First Users

Users are created by you (admin) — this is **not** open registration. Residents cannot sign up on their own.

### Step 8.1: Create Your Admin Account

1. Go to your Supabase project → **"Authentication"** → **"Users"**
2. Click **"Invite user"**
3. Enter your email address
4. Check your email for the invite link — click it to set your password
5. After you've set your password, go back to Supabase → Authentication → Users
6. Click on your user row
7. Scroll down to **"User Metadata"** and click **"Edit"**
8. Replace the metadata with:
   ```json
   {
     "role": "admin",
     "display_name": "Dr. Michael Scholl"
   }
   ```
9. Click **"Save"**

Now go to https://slbfm.com and log in. You should land on `/admin/users`.

### Step 8.2: Add Faculty Users

Repeat Step 8.1 for each faculty member. Set role to `"faculty"` in the metadata:
```json
{
  "role": "faculty",
  "display_name": "Dr. Colleague Name"
}
```

Faculty users land on `/faculty/search` after login.

### Step 8.3: Add Resident Users

For each resident:
1. Supabase → Authentication → Invite user → their email
2. After they accept the invite, set their metadata:
   ```json
   {
     "role": "resident",
     "display_name": "Dr. Resident Name"
   }
   ```
3. In your Netlify site → Admin panel (`/admin/users`), set their `cohort_year` and `abfm_id`

> **A trigger runs automatically:** When a new user is created via the Supabase invite flow, a database trigger (`handle_new_user()` defined in `005_functions.sql`) automatically creates a `user_profiles` row for them. You don't need to do this manually.

---

## 12. Troubleshooting

### "Module not found" during npm install or build

```bash
cd 05_module.5_web/frontend
rm -rf node_modules
npm install
```

If that doesn't fix it, check your Node.js version: `node --version` — it should be v20 or higher.

### Supabase connection errors ("fetch failed", "network error")

- Check that `NEXT_PUBLIC_SUPABASE_URL` is correct (no trailing slash)
- Check that `NEXT_PUBLIC_SUPABASE_ANON_KEY` is the **anon** key, not the service_role key

### "relation does not exist" in Supabase

One of the migrations didn't run, or ran out of order. Check which tables exist:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
```
Then re-run the missing migration from Step 1.3.

### Railway won't start / "No module named 'ite_parser'"

You forgot to copy the parser files. Run:
```bash
cp 03_module.3_analyst/scripts/ite_parser.py 05_module.5_web/api/parser/
cp 03_module.3_analyst/scripts/ite_parser_config.json 05_module.5_web/api/parser/
```
Then commit and push — Railway redeploys automatically on every GitHub push.

### Netlify build fails with TypeScript errors

Run this locally to see the errors:
```bash
cd 05_module.5_web/frontend
npm run type-check
```

Fix the flagged issues and push again. TypeScript errors are often caused by missing or incorrect types in `lib/supabase/types.ts`.

### NL search returns no results

1. Check OpenAI API key is set correctly
2. Verify vectors were synced: in Supabase SQL Editor, run:
   ```sql
   SELECT COUNT(*) FROM question_icd10_vec;
   ```
   Expected: ~2,747 rows. If 0, re-run `vector_sync.py`.

### "Invalid login credentials" for a user you just created

The user may not have accepted the invite email yet. Check their email. Invites expire after 24 hours — you can resend from Supabase → Authentication → Users → click the user → "Send magic link".

### The site works locally but not on Netlify

Almost always an environment variable problem. Double-check every variable in Netlify → Site configuration → Environment variables, especially:
- No extra spaces before/after the value
- The `NEXT_PUBLIC_` prefix is correct for public vars
- The service_role key is included (it's easy to forget since it's not in `.env.example` as a required field for some flows)

---

## 13. Day-to-Day: After It's Live

### When you run M1/M2/M3 pipeline updates

After any pipeline run that changes data in `ite_intelligence.db`, sync to Supabase:

```bash
# Sync content tables (articles, questions, etc.)
python 05_module.5_web/supabase/sync/sqlite_to_supabase.py

# Only needed if vector embeddings changed (rare)
python 05_module.5_web/supabase/sync/vector_sync.py
```

You do NOT need to redeploy the website — it reads from Supabase dynamically.

### When you push code changes

Netlify auto-deploys every time you push to `main`. The build takes 3–5 minutes. You can watch progress in Netlify → Deploys.

### When you need to update curriculum

Go to https://slbfm.com/faculty/curriculum (the embedded Sanity Studio) or run the Sanity Studio locally (`cd 05_module.5_web/sanity && npm run dev`) and make your changes there.

### When a resident uploads their score report

It happens automatically — they upload the PDF on the site, it goes to Supabase Storage, Railway parses it, and results appear in their analytics dashboard within ~30 seconds. You don't need to do anything.

### When ite_parser.py is updated in M3

Copy the new version to the API directory and push:
```bash
cp 03_module.3_analyst/scripts/ite_parser.py 05_module.5_web/api/parser/
cp 03_module.3_analyst/scripts/ite_parser_config.json 05_module.5_web/api/parser/
git add 05_module.5_web/api/parser/
git commit -m "update: parser from M3"
git push
```
Railway will redeploy automatically.

---

## Quick Reference: The Checklist

Use this as a launch checklist:

- [ ] Supabase account created, project created
- [ ] pgvector extension enabled
- [ ] All 5 migrations run in order (001→005)
- [ ] `score-reports` Storage bucket created (private)
- [ ] Supabase credentials saved (URL, anon key, service_role key, DB URL)
- [ ] `pip install supabase python-dotenv tqdm psycopg2-binary`
- [ ] `.env` created in repo root with Supabase credentials
- [ ] `sqlite_to_supabase.py` run successfully
- [ ] `vector_sync.py` run successfully
- [ ] NL search validation returns results
- [ ] Railway account created, project connected to GitHub
- [ ] `05_module.5_web/api` set as Railway root directory
- [ ] Railway env vars set (SUPABASE_URL, SUPABASE_SERVICE_KEY, PARSER_SECRET, ENV)
- [ ] Railway `/health` endpoint returns `{"status": "ok"}`
- [ ] Parser files copied to `05_module.5_web/api/parser/`
- [ ] Sanity account created, `npx sanity init` run, Project ID saved
- [ ] Node.js v20+ installed
- [ ] `npm install` in `05_module.5_web/frontend`
- [ ] `.env.local` created with all 8 variables
- [ ] `npm run dev` runs locally without errors
- [ ] Admin user created in Supabase Auth, can log in locally
- [ ] Netlify account created, repo connected
- [ ] Netlify build settings configured (base dir, build command)
- [ ] All env vars added to Netlify
- [ ] Netlify build succeeds
- [ ] slbfm.com domain added to Netlify
- [ ] DNS nameservers updated to Netlify
- [ ] HTTPS working (green padlock at https://slbfm.com)
- [ ] First resident invited and tested end-to-end

---

*Guide covers the full stack as designed in `05_module.5_web/`. For architecture details, see `05_module.5_web/README.md`. For DB schema, see `00_database/DATABASE_GUIDE.md`.*
