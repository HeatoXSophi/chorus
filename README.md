# 🎵 Chorus - AI Skills Marketplace (Production)

Chorus is an open marketplace for AI agents. It allows developers to publish Python functions as "skills" and monetize them, while users can discover and hire these skills via a web portal.

## 🚀 Live Demo

[View Live Demo](https://chorus.vercel.app) *(Replace with your Vercel URL after deployment)*

## 🏗️ Architecture

This project is built with a serverless-first approach:

- **Frontend**: Vanilla JS + CSS (located in `/portal`)
- **Backend**: Supabase (PostgreSQL + Auth + Edge Functions)
- **SDK**: Python client (`chorus_sdk`) that connects to Supabase REST API
- **Agents**: Hybrid (Local execution) or Serverless (Cloud Functions)

## 🛠️ Setup for Development

### Prerequisites

- Python 3.9+
- Node.js (optional, for Vercel CLI)
- Docker (optional, for local Supabase dev)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and add your Supabase credentials:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### 3. Run the Portal Locally

```bash
start_chorus.bat
```

Visit http://localhost:8888

### 4. Run the Python SDK Demo

```bash
python demo/supabase_demo.py
```

## 📦 Deployment

### Frontend (Vercel)

This project is configured for Vercel.

1.  Push to GitHub.
2.  Import project in Vercel.
3.  Set Output Directory to `portal`.
4.  Deploy!

### Backend (Supabase)

1.  Create a project on Supabase.
2.  Run the SQL migration in `supabase_schema.sql` via SQL Editor.
3.  Get your API URL and Key.
4.  Update `portal/js/config.js` with your keys.

## 📄 License

MIT
