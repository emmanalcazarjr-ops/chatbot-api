# Rush AI Butler API

An AI-powered customer support chatbot built with FastAPI and DeepSeek AI. Rush maintains conversation memory across sessions, supports webhook integrations for automation platforms (n8n, Zapier, Make, GoHighLevel), and includes rate limiting and API key authentication. The chatbot is designed to answer questions about Emmanuel's projects, skills, and experience, making it a conversational portfolio assistant.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12 |
| Framework | FastAPI |
| AI Model | DeepSeek AI (deepseek-chat) |
| Database | Neon PostgreSQL (conversation history) |
| Deployment | Vercel Serverless Functions |
| Docs | Auto-generated Swagger UI |

## Features

- Conversational AI with session-based memory
- Webhook support for n8n, Zapier, Make, and GoHighLevel
- API key authentication for protected endpoints
- Rate limiting to prevent abuse
- Conversation history persistence in PostgreSQL
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
  "response": "Emmanuel has built several impressive projects including a Fraud Detection System, RAG Document Q&A API, and a Core Banking System...",
  "done": true
}
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek AI API key | Yes |
| `DATABASE_URL` | Neon PostgreSQL connection string | Yes |
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
export DEEPSEEK_API_KEY="your-key"
export DATABASE_URL="your-neon-url"
export API_KEY="your-api-key"

# Run locally
uvicorn api.index:app --reload
```

## Live Demo

- API: https://chatbot-api-two-teal.vercel.app
- Landing Page: https://chatbot-api-two-teal.vercel.app
- Swagger Docs: https://chatbot-api-two-teal.vercel.app/docs

## Author

**Emmanuel L. Alcazar Jr.**
- GitHub: [@emmanalcazarjr-ops](https://github.com/emmanalcazarjr-ops)
- Portfolio: [portfolio-elalcazarjr.vercel.app](https://portfolio-elalcazarjr.vercel.app)
