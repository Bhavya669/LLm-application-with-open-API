# Flask + MongoDB + Gemini AI API

A Python Flask backend that accepts user questions, retrieves a configurable prompt template from MongoDB, sends the final prompt to the Google Gemini API, stores every request/response in MongoDB history, and returns the AI response as JSON.

---

## Project Structure

```
pythonnn/
├── app.py                    # Flask application factory + health endpoint
├── config.py                 # Environment variable loading and validation
├── requirements.txt          # Project dependencies
├── .env                      # Your local secrets (never commit this)
├── .env.example              # Placeholder template (safe to commit)
├── .gitignore                # Ignores .env, venv, __pycache__
├── database/
│   └── mongodb.py            # MongoDB client, db, collections
├── routes/
│   └── ai_routes.py          # /ask and /ask-batch endpoints
└── services/
    ├── prompt_service.py     # Fetches prompt templates from MongoDB
    ├── openai_service.py     # Gemini API calls (single + concurrent bulk)
    └── history_service.py    # Saves request/response to MongoDB history
```

---

## Architecture

```
Client
  |
  | HTTP POST
  v
Flask API (/ask or /ask-batch)
  |
  +---> MongoDB (prompts collection)
  |         Fetch "Education Prompt" template
  |
  +---> Replace {{userInput}} with actual input
  |
  +---> Google Gemini API
  |         Generate AI response
  |
  +---> MongoDB (history collection)
  |         Save userInput + response + timestamp
  |
  v
JSON response to client
```

For batch requests, all Gemini API calls are executed concurrently using `asyncio.gather()` + `asyncio.to_thread()`, and results are returned in the same order as the input list.

---

## Technologies

- Python 3.13
- Flask 3.1.1
- MongoDB (local or Atlas)
- PyMongo 4.10.1
- Google Gemini API (`google-genai` SDK)
- python-dotenv
- asyncio (for concurrent batch processing)

---

## Prerequisites

- Python 3.11 or higher installed
- MongoDB running locally on `mongodb://localhost:27017` (or a MongoDB Atlas URI)
- A Google Gemini API key — get one free at https://aistudio.google.com/app/apikey

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Open the `.env` file in the project root and fill in your values:

```
GEMINI_API_KEY=your_actual_gemini_api_key_here
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=ai_project
GEMINI_MODEL=gemini-3.6-flash
```

Never commit the `.env` file. It is already listed in `.gitignore`.

### 3. Set up MongoDB

Make sure MongoDB is running. Then insert the required prompt document into the `ai_project` database.

Open `mongosh` or MongoDB Compass and run:

```js
use ai_project

db.prompts.insertOne({
  "_id": "Education Prompt",
  "template": "You are an expert in education domain. Answer the following: {{userInput}}"
})
```

This document is the prompt template the application fetches on every request. The placeholder `{{userInput}}` is replaced with the user's actual question at runtime.

### 4. Start the server

```bash
python app.py
```

You should see:

```
Starting Flask development server...
* Running on http://127.0.0.1:5000
* Running on http://0.0.0.0:5000
```

The server runs on port `5000` by default.

---

## API Endpoints

### GET /health

Checks that Flask is running and MongoDB is reachable.

```
GET http://localhost:5000/health
```

Response (success):
```json
{
  "status": "ok",
  "mongodb": "connected"
}
```

Response (MongoDB unreachable):
```json
{
  "status": "error",
  "mongodb": "unreachable"
}
```

---

### POST /ask

Accepts a single user question. Fetches the prompt template from MongoDB, substitutes the user's input, calls Gemini, saves the result to history, and returns the AI response.

**Request**

```
POST http://localhost:5000/ask
Content-Type: application/json
```

```json
{
  "userInput": "How much should I score in each subject to pass CA final?"
}
```

**Success Response — HTTP 200**

```json
{
  "response": "To pass the CA Final exam, you generally need to score..."
}
```

**Error Responses**

| Scenario | HTTP Status | Response |
|---|---|---|
| Missing body | 400 | `{"error": "Request body must be valid JSON."}` |
| Missing userInput | 400 | `{"error": "userInput is required."}` |
| Empty string | 400 | `{"error": "userInput must be a non-empty string."}` |
| Prompt not in MongoDB | 404 | `{"error": "Prompt configuration not found. Contact administrator."}` |
| MongoDB error | 500 | `{"error": "Database error. Please try again later."}` |
| Gemini API error | 500 | `{"error": "AI service error. Please try again later."}` |

---

### POST /ask-batch

Accepts a list of questions. Fetches the prompt template once, substitutes each input independently, calls Gemini for all inputs concurrently, saves each result to history, and returns all responses in the original input order.

**Request**

```
POST http://localhost:5000/ask-batch
Content-Type: application/json
```

```json
{
  "userInput": [
    "What is Python?",
    "What is machine learning?",
    "What is Flask?"
  ]
}
```

**Success Response — HTTP 200**

```json
{
  "responses": [
    "Python is a high-level, interpreted programming language...",
    "Machine learning is a subset of artificial intelligence...",
    "Flask is a lightweight web framework for Python..."
  ]
}
```

The order of responses always matches the order of the input list, regardless of which Gemini call completes first.

If one individual input fails, its slot in the responses array returns an error object while the rest succeed:

```json
{
  "responses": [
    "Python is a high-level...",
    {"error": "AI service error for this input."},
    "Flask is a lightweight..."
  ]
}
```

**Error Responses**

| Scenario | HTTP Status | Response |
|---|---|---|
| Missing body | 400 | `{"error": "Request body must be valid JSON."}` |
| userInput is a string, not a list | 400 | `{"error": "userInput must be a list of strings."}` |
| Empty list | 400 | `{"error": "userInput list must not be empty."}` |
| Invalid item in list | 400 | `{"error": "Each item in userInput must be a non-empty string. Invalid item at index N."}` |
| Prompt not in MongoDB | 404 | `{"error": "Prompt configuration not found. Contact administrator."}` |
| MongoDB error | 500 | `{"error": "Database error. Please try again later."}` |

---

## Testing with Postman

### Test 1 — Health check

```
GET http://localhost:5000/health
```

Expected: `{"status": "ok", "mongodb": "connected"}`

---

### Test 2 — Single question

```
POST http://localhost:5000/ask
Content-Type: application/json

{
  "userInput": "How much should I score in each subject to pass CA final?"
}
```

Expected: `{"response": "..."}` with a real AI answer.

---

### Test 3 — Missing input (should return 400)

```
POST http://localhost:5000/ask
Content-Type: application/json

{}
```

Expected: HTTP 400 — `{"error": "userInput is required."}`

---

### Test 4 — Batch questions

```
POST http://localhost:5000/ask-batch
Content-Type: application/json

{
  "userInput": [
    "What is Python?",
    "What is machine learning?",
    "What is Flask?"
  ]
}
```

Expected: `{"responses": ["...", "...", "..."]}` — three answers in the same order.

---

### Test 5 — Invalid batch (string instead of list, should return 400)

```
POST http://localhost:5000/ask-batch
Content-Type: application/json

{
  "userInput": "What is Python?"
}
```

Expected: HTTP 400 — `{"error": "userInput must be a list of strings."}`

---

### Test 6 — Empty list (should return 400)

```
POST http://localhost:5000/ask-batch
Content-Type: application/json

{
  "userInput": []
}
```

Expected: HTTP 400 — `{"error": "userInput list must not be empty."}`

---

## Verifying MongoDB History

After making any successful request to `/ask` or `/ask-batch`, open MongoDB Compass:

1. Connect to `mongodb://localhost:27017`
2. Open database `ai_project`
3. Open collection `history`
4. Each document will look like:

```json
{
  "_id": ObjectId("..."),
  "userInput": "What is Python?",
  "response": "Python is a high-level, interpreted programming language...",
  "createdAt": 2026-09-03T12:00:00.000+00:00
}
```

For a batch request with 3 inputs, you will see 3 separate documents — one per input.

---

## How Concurrent Batch Processing Works

When `/ask-batch` receives multiple inputs:

1. The prompt template is fetched from MongoDB once.
2. Each input is substituted into the template independently.
3. All Gemini API calls are dispatched at the same time using `asyncio.gather()`.
4. Each blocking Gemini call runs in its own thread via `asyncio.to_thread()` so they truly execute concurrently.
5. Results are collected in the original input order — not completion order.
6. Each result is saved to MongoDB history independently.

This means 5 questions take roughly the same time as 1 question, rather than 5x longer.

---

## Security Notes

- The `GEMINI_API_KEY` and `MONGODB_URI` are loaded from `.env` and never appear in source code, logs, or API responses.
- The `.env` file is listed in `.gitignore` and will not be committed to Git.
- API errors are caught and returned as generic safe messages — no stack traces or internal details are exposed to the client.
