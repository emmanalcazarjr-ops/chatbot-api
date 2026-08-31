# Rush AI Butler API

[![CI](https://github.com/emmanalcazarjr-ops/chatbot-api/actions/workflows/ci.yml/badge.svg)](https://github.com/emmanalcazarjr-ops/chatbot-api/actions/workflows/ci.yml)
![Tests](https://img.shields.io/badge/tests-10%20passing-brightgreen)

An AI-powered customer support chatbot built with FastAPI and Google Gemini AI. Rush maintains conversation memory across sessions, supports webhook integrations for automation platforms (n8n, Zapier, Make, GoHighLevel), and includes rate limiting and API key authentication. The chatbot is designed to answer questions about Emmanuel's projects, skills, and experience, making it a conversational portfolio assistant.

**Production practices:** CI pipeline (GitHub Actions) runs the unit-test suite on every push — API contract tests via FastAPI TestClient, offline AI client tests, and session-memory persistence checks.


## Screenshots

| Landing Page | API Docs (Swagger UI) |
|---|---|
| ![Landing Page](screenshots/home.png) | ![API Docs](screenshots/docs.png) |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| Framework | FastAPI |
| AI Model | Google Gemini AI (gemini-3.7-flash) |
| Database | Neon PostgreSQL / Supabase (conversation history) |
| Deployment | Vercel Serverless Functions |
| Docs | Auto-generated Swagger UI |

## Features

- Conversational AI with session-based memory
- Webhook support for n8n, Zapier, Make, and GoHighLevel
- API key authentication for protected endpoints
- Rate limiting to prevent abuse
- Conversation history persistence in PostgreSQL / Supabase
- Interactive Swagger documentation at `/docs`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send a message to Rush |
| GET | `/api/chat/history/{session_id}` | Get conversation history |
| DELETE | `/api/chat/{session_id}` | Clear conversation |
| POST | `/api/webhook` | Receive messages from automation platforms |
| GET | `/api/health` | Health check |
| GET | `/docs` | Interactive API documentation (Swagger UI) |

### Example Request

```bash
curl -X POST https://chatbot-api-two-teal.vercel.app/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"message": "Tell me about Emmanuel\'s projects", "session_id": "optional-session-id"}'
```

### Example Response

```json
{
  "session_id": "abc-123",
  "response": "Emmanuel has built several impressive projects including an Automated Report Generator, Water Station Telegram Bots, and Rush Personal Assistant...",
  "done": true
}
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `API_KEY` | API key for authenticated endpoints | Yes |

## Local Development

```bash
# Clone the repository
git clone https://github.com/emmanalcazarjr-ops/chatbot-api.git
cd chatbot-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY="your-gemini-key"
export DATABASE_URL="your-neon-url"
export API_KEY="your-api-key"

# Run locally
uvicorn api.main:app --reload
```

## Live Demo

- API: https://chatbot-api-two-teal.vercel.app
- Docs: https://chatbot-api-two-teal.vercel.app/docs
- Health: https://chatbot-api-two-teal.vercel.app/api/health

---

## Case Study: Portfolio AI Butler

**Problem:** Recruiters and clients visit a portfolio with specific questions about skills, experience, and project architecture, but static text cannot answer dynamic follow-ups or explain system design choices interactively.

**Solution:** Built a production-ready conversational API that acts as an interactive representative. It maintains state across conversations, integrates with automation webhooks, and is protected with authentication and rate limiting.

**Business Value:**
- **24/7 Availability:** Answers candidate and client inquiries instantly without manual effort.
- **Enterprise Integrations:** Webhook architecture allows direct connection to CRM pipelines and lead capture forms (n8n, Zapier, Make).
- **Abuse Protection:** Per-client rate limiting and API key protection prevent denial-of-wallet attacks and service degradation.

**Tools & Technologies:** Python 3.12, FastAPI, Google Gemini AI (gemini-3.7-flash), Supabase / Neon PostgreSQL, Vercel Serverless Functions, Swagger UI

**Architecture Highlights:**
- Stateless serverless deployment on Vercel with external persistent memory in PostgreSQL.
- Isolated model integration layer with graceful error handling.
- Layered middleware for authentication and rate limiting.

**What I built:** The full backend API (chat, history, webhook, health endpoints), Gemini integration layer, PostgreSQL schema, rate limiting and auth middleware, Vercel deployment config, and the landing-page demo.A production-grade conversational AI assistant deployed live on Vercel, available 24/7 to any number of concurrent visitors.

**Business Impact:**
- Gives employers and clients an immediate, interactive demonstration of AI engineering skills
- Automates first-contact Q&A, reducing friction for recruiters and visitors
- Shows production-level engineering: authentication, rate limiting, persistence, webhooks, and auto-generated docs

**What I built:** The full backend API (chat, history, webhook, health endpoints), DeepSeek integration layer, PostgreSQL schema, rate limiting and auth middleware, Vercel deployment config, and the landing-page demo.

## Author

**Emmanuel L. Alcazar Jr.**
- GitHub: [@emmanalcazarjr-ops](https://github.com/emmanalcazarjr-ops)
- Portfolio: [portfolio-elalcazarjr.vercel.app](https://portfolio-elalcazarjr.vercel.app)
