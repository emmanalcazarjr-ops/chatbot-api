# Rush AI Butler API

AI-powered customer support butler built with FastAPI and DeepSeek AI.

## Endpoints

**POST** `/api/chat` - Send a message to Rush

```json
{
  "message": "Tell me about Emmanuel's projects",
  "session_id": "optional-session-id"
}
```

Response:
```json
{
  "session_id": "abc-123",
  "response": "Emmanuel has built several impressive projects...",
  "done": true
}
```

**GET** `/api/chat/history/{session_id}` - Get conversation history

**DELETE** `/api/chat/{session_id}` - Clear conversation

**POST** `/api/webhook` - Receive messages from n8n/Zapier/Make/GoHighLevel

**GET** `/api/health` - Health check

**GET** `/docs` - Interactive API documentation (Swagger UI)

## Tech Stack

- Python 3.12
- FastAPI
- DeepSeek AI
- Neon PostgreSQL
- Vercel

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DEEPSEEK_API_KEY` | DeepSeek AI API key |
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `API_KEY` | API key for authenticated endpoints |

## Deploy

Push to GitHub and connect to Vercel.

## Live

- API: https://chatbot-api-two-teal.vercel.app
- Landing Page: https://chatbot-api-two-teal.vercel.app
- Swagger Docs: https://chatbot-api-two-teal.vercel.app/docs
