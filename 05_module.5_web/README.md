# 05_module.5_web — Board Prep Intel Interactive Layer

Interactive web platform for the ABFM ITE Intelligence System.  Two audiences:
residents (assessments, analytics, prescribed reading) and faculty (NL question search, curriculum management).

---

## Architecture

```
Next.js (App Router)     → Netlify (frontend + API routes)
Supabase (PostgreSQL)    → cloud DB + auth + pgvector + storage
Sanity CMS               → curriculum content (sessions, assignments, readings)
Railway FastAPI          → PDF score report parser (Python microservice)
OpenAI API               → NL query embedding (text-embedding-3-small)
```

---

## Directory Structure

```
05_module.5_web/
├── frontend/            ← Next.js 15 app (TypeScript, App Router)
│   ├── app/
│   │   ├── page.tsx                     ← landing/redirect by role
│   │   ├── login/page.tsx               ← email+password auth
│   │   ├── resident/
│   │   │   ├── dashboard/page.tsx       ← assignments, sessions, announcements
│   │   │   ├── assessment/[id]/page.tsx ← question-by-question exam
│   │   │   ├── scores/upload/page.tsx   ← PDF upload → Railway parser
│   │   │   ├── analytics/page.tsx       ← radar + bar charts + watch-list
│   │   │   └── library/page.tsx         ← prescribed reading list
│   │   ├── faculty/
│   │   │   ├── search/page.tsx          ← NL question + article search (Dr. XYZ)
│   │   │   ├── question-sets/page.tsx   ← saved search results
│   │   │   ├── articles/page.tsx        ← browse/filter article library
│   │   │   └── curriculum/page.tsx      ← embedded Sanity Studio
│   │   ├── admin/
│   │   │   ├── users/page.tsx           ← user management
│   │   │   └── sync/page.tsx            ← DB sync status + instructions
│   │   └── api/
│   │       ├── auth/callback/route.ts   ← Supabase PKCE exchange
│   │       ├── search/route.ts          ← POST NL search (server-side OpenAI embed)
│   │       └── scores/upload/route.ts   ← POST PDF → Storage → Railway trigger
│   ├── components/
│   │   ├── resident/
│   │   │   ├── AssessmentRunner.tsx     ← client-side exam interface
│   │   │   └── AnalyticsDashboard.tsx   ← Recharts radar + bar + watch-list
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts                ← browser client
│   │   │   ├── server.ts                ← server client + admin client
│   │   │   └── types.ts                 ← TypeScript types (expand with supabase gen)
│   │   ├── sanity/client.ts             ← GROQ queries
│   │   └── search/nl-search.ts         ← NL search pipeline (embed → vector → fetch)
│   ├── middleware.ts                    ← auth guard + role-based routing
│   └── netlify.toml                    ← Netlify build config
│
├── sanity/              ← Sanity Studio (curriculum CMS)
│   ├── sanity.config.ts
│   └── schemas/
│       ├── residentCohort.ts
│       ├── curriculumSession.ts
│       ├── prescribedReading.ts         ← stores article_id refs (not data)
│       ├── assessmentAssignment.ts      ← dynamic or static QID sets
│       └── facultyAnnouncement.ts
│
├── supabase/            ← Database migrations + sync scripts
│   ├── migrations/
│   │   ├── 001_core_schema.sql          ← articles, questions, xref, ICD-10
│   │   ├── 002_vector_tables.sql        ← pgvector tables + search functions
│   │   ├── 003_resident_tables.sql      ← resident_scores, sessions, uploads
│   │   ├── 004_rls_policies.sql         ← Row Level Security
│   │   └── 005_functions.sql            ← analytics Postgres functions
│   └── sync/
│       ├── sqlite_to_supabase.py        ← content sync (all non-vector tables)
│       └── vector_sync.py               ← embedding sync (pgvector COPY)
│
└── api/                 ← Python FastAPI microservice (Railway)
    ├── main.py                          ← /health + /parse-score-report
    ├── requirements.txt
    ├── Procfile
    ├── railway.json
    └── parser/
        └── README.md                    ← copy ite_parser.py here before deploy
```

---

## Setup Order

### 1. Supabase

1. Create a Supabase project at https://supabase.com
2. Enable pgvector: Dashboard → SQL Editor → `CREATE EXTENSION IF NOT EXISTS vector;`
3. Run migrations in order: `001` → `002` → `003` → `004` → `005`
4. Enable Supabase Storage: create a bucket named `score-reports` (private)
5. Note your `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`

### 2. Sync Data

```bash
# Install dependencies
pip install supabase python-dotenv tqdm psycopg2-binary

# Set env vars (or create .env in project root)
export SUPABASE_URL=https://xxxxx.supabase.co
export SUPABASE_SERVICE_KEY=eyJhbGc...
export SUPABASE_DB_URL=postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres

# Sync content tables
python 05_module.5_web/supabase/sync/sqlite_to_supabase.py

# Sync vector embeddings (requires rebuilt embeddings in SQLite)
python 05_module.5_web/supabase/sync/vector_sync.py
```

### 3. Validate NL Search

```bash
export OPENAI_API_KEY=sk-...
python 04_module.4_sandbox/scripts/nl_search_validation.py "abdominal pain acute and chronic" --count 15
```

This confirms embeddings are loaded and the pgvector index is functional before building the UI.

### 4. Sanity

```bash
cd 05_module.5_web/sanity
npm install
npx sanity init           # creates project + dataset, updates sanity.config.ts
npm run dev               # local studio at http://localhost:3333
```

Create curriculum sessions, cohorts, and your first assessment assignment.

### 5. Railway (Score Parser API)

```bash
# Copy parser source files
cp 03_module.3_analyst/scripts/ite_parser.py 05_module.5_web/api/parser/
cp 03_module.3_analyst/scripts/ite_parser_config.json 05_module.5_web/api/parser/

# Deploy: connect 05_module.5_web/api/ to Railway
# Set env vars in Railway dashboard:
#   SUPABASE_URL, SUPABASE_SERVICE_KEY, PARSER_SECRET
```

### 6. Next.js Frontend

```bash
cd 05_module.5_web/frontend
npm install
cp .env.example .env.local   # fill in your keys
npm run dev                   # http://localhost:3000
```

Deploy to Netlify: connect the repo, set root directory to `05_module.5_web/frontend`, add env vars.

---

## Environment Variables

| Variable | Used By | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Frontend | Public — safe in browser |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Frontend | Public — RLS enforces isolation |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side API routes | **Never expose to client** |
| `NEXT_PUBLIC_SANITY_PROJECT_ID` | Frontend | Public |
| `NEXT_PUBLIC_SANITY_DATASET` | Frontend | Public |
| `OPENAI_API_KEY` | Server-side `/api/search` | **Never expose to client** |
| `SCORE_PARSER_API_URL` | Server-side `/api/scores/upload` | Railway app URL |
| `SCORE_PARSER_API_SECRET` | Server-side + Railway | Shared webhook auth secret |
| `SUPABASE_URL` | Sync scripts + Railway | Server-side |
| `SUPABASE_SERVICE_KEY` | Sync scripts + Railway | Server-side |
| `SUPABASE_DB_URL` | `vector_sync.py` | PostgreSQL direct connection |

---

## NL Search Flow

```
User types: "give me 15 questions on abdominal pain — acute, chronic, peds"
    │
    ▼
/api/search (server-side Route Handler)
    │
    ├── OpenAI text-embedding-3-small → 1536-dim vector
    ├── Supabase RPC search_questions_by_embedding → ranked QIDs
    ├── Fetch question rows (ITE + AAFP)
    ├── JOIN qid_art_xref → article_ids
    └── Fetch article rows → return to client
    │
    ▼
Faculty UI: questions (left) + articles (right) side-by-side
    └── "Save as Question Set" → question_sets table → assign via Sanity
```

---

## Data Flow: Score Upload

```
Resident uploads PDF
    │
    ▼
/api/scores/upload
    ├── Validate auth (resident role)
    ├── Upload PDF → Supabase Storage (score-reports/{uid}/{year}/)
    ├── Create score_uploads row (status=pending)
    └── POST /parse-score-report → Railway
            │
            ▼
        Railway FastAPI
            ├── Download PDF from Supabase Storage
            ├── ite_parser.parse_blueprint() → item list
            ├── Map item numbers → QIDs (exam_year order)
            ├── Upsert → resident_scores
            └── Update score_uploads (status=complete)
            │
            ▼
    Resident analytics dashboard reads resident_scores via Supabase
```

---

## Adding Users

Users are provisioned by the program director (admin), not open registration.

1. Supabase Dashboard → Authentication → Users → Invite User
2. Set `raw_user_meta_data`:
   ```json
   { "role": "resident", "display_name": "Dr. Jane Smith" }
   ```
3. The `handle_new_user()` trigger auto-creates the `user_profiles` row.
4. For residents: update their `cohort_year` and `abfm_id` in the admin UI.
