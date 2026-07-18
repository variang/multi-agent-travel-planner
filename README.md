# WanderWise — Multi-Agent Travel Planner

A multi-agent AI travel assistant built with [Google ADK](https://google.github.io/adk-docs/) and Gemini. WanderWise orchestrates six specialized sub-agents to deliver a complete travel plan: personalized itinerary, current events, weather forecast, and a packing list — all from a single natural-language query.

## Architecture

```
User Query
    │
    ▼
┌────────────────────────────────────┐
│   wanderwise_coordinator_agent     │  ← routes & orchestrates
└────┬───────┬───────┬───────┬───────┘
     │       │       │       │
     ▼       ▼       ▼       ▼
 itinerary  events  weather  personalizer
  agent     agent   agent    agent
                               │
                               ▼
                         packing_list
                            agent
```

| Agent | Responsibility |
|---|---|
| `itinerary_agent` | Creates day-by-day travel itinerary using Google Search |
| `latest_events_agent` | Finds current events & festivals via Google Search |
| `weather_agent` | Current weather & 5-day forecast via OpenWeatherMap |
| `personalized_itinerary_agent` | Merges itinerary with relevant events |
| `packing_list_agent` | Generates a packing list from itinerary + weather |
| `wanderwise_coordinator_agent` | Top-level orchestrator; routes queries to sub-agents |

## Prerequisites

- Python 3.10+
- A [Google Cloud](https://cloud.google.com/) project with the **Vertex AI API** enabled, **or** a [Google AI Studio](https://aistudio.google.com/) API key
- An [OpenWeatherMap](https://openweathermap.org/api) API key (free tier is sufficient)

## Setup

### 1. Clone & install dependencies

```bash
git clone https://github.com/variang/multi-agent-travel-planner.git
cd multi-agent-travel-planner
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Open `.env` and fill in the values (see sections below).

---

## LLM Connection Options

### Option A — Google AI Studio (API Key, simplest)

```dotenv
# .env
GOOGLE_GENAI_USE_VERTEXAI=False
GOOGLE_API_KEY=YOUR_GOOGLE_AI_STUDIO_API_KEY
OPEN_WEATHER_API_KEY=YOUR_OPENWEATHER_KEY
```

Get a free API key at <https://aistudio.google.com/apikey>.

---

### Option B — Vertex AI via Service Account (recommended for production)

This uses a **Google Cloud Service Account JSON key** to authenticate with the Vertex AI Gemini API.

#### Step 1 — Create a Service Account

1. Go to [IAM & Admin → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts) in the Cloud Console.
2. Click **Create Service Account**, give it a name (e.g. `wanderwise-sa`), and click **Create and Continue**.
3. Grant the role **Vertex AI User** (`roles/aiplatform.user`), then click **Done**.

#### Step 2 — Download the JSON key

1. Click your new service account → **Keys** tab → **Add Key → Create new key → JSON**.
2. Save the downloaded file, e.g. as `service-account.json` (keep it outside the repo or add it to `.gitignore`).

#### Step 3 — Set environment variables

```dotenv
# .env
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1          # or your preferred region
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
OPEN_WEATHER_API_KEY=YOUR_OPENWEATHER_KEY
```

> **Tip:** Never commit the JSON key or `.env` to version control. Both are listed in `.gitignore`.

#### Alternative — Application Default Credentials (ADC)

If you're running on GCE / Cloud Run / GKE, or have already run `gcloud auth application-default login`, you can omit `GOOGLE_APPLICATION_CREDENTIALS` and ADC is used automatically.

```bash
gcloud auth application-default login
```

---

## Observability with Langfuse (optional)

WanderWise integrates with [Langfuse](https://langfuse.com/) for tracing agent runs. Tracing is **opt-in** — the app works fine without it.

### Start a local Langfuse instance

Docker is required. A `docker-compose.langfuse.yml` is included in the repo.

```bash
# 1. Start the Docker daemon (macOS with Colima)
colima start

# 2. Start Langfuse + its Postgres database
docker compose -f docker-compose.langfuse.yml up -d
```

Langfuse will be available at <http://localhost:3000>.

### Create an account and generate API keys

1. Open <http://localhost:3000> and register a new account.
2. Create an **organisation** and a **project**.
3. Go to **Settings → API Keys** and create a new key pair.

### Add the keys to your `.env`

```dotenv
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=http://localhost:3000
LANGFUSE_HOST=http://localhost:3000
```

> **Note:** Keys generated on Langfuse Cloud will not work against a local instance and vice versa — always use keys from the same instance you are pointing to.

### Stopping Langfuse

```bash
docker compose -f docker-compose.langfuse.yml down
```

---

## Running the Planner

```bash
python main.py
```

This starts an interactive CLI. Type your travel request and press Enter. Type `exit` or `quit` to stop.

To run the canned evaluation test cases:

```bash
python eval_test.py
```

### Example queries

```python
"I will be in Milan for 3 days this weekend. I love fashion and food. What should I pack?"
"Plan a 5-day trip to Cairo in September. I love ancient history and local cuisine."
"What events are happening in Munich at the end of July? Any packing tips?"
"What's the current weather in Tokyo?"
```

## Project Structure

```
multi-agent-travel-planner/
├── agents/
│   ├── __init__.py
│   ├── weather_agent.py         # Current & forecast weather (OpenWeatherMap)
│   ├── itinerary_agent.py       # Day-by-day itinerary (Google Search)
│   ├── events_agent.py          # Events & festivals (Google Search)
│   ├── personalizer_agent.py    # Merges itinerary + events
│   └── packing_list_agent.py    # Packing list generator
├── tools/
│   ├── __init__.py
│   └── weather_tools.py         # Custom OpenWeatherMap tool functions
├── coordinator.py               # Coordinator agent + wrapper tools
├── tracing_utils.py             # Langfuse tracing helpers (optional)
├── main.py                      # Interactive CLI entry point
├── eval_test.py                 # Canned evaluation test cases
├── docker-compose.langfuse.yml  # Local Langfuse + Postgres stack
├── requirements.txt
├── .env.example
└── README.md
```

## Key Dependencies

| Package | Purpose |
|---|---|
| `google-adk` | Agent Development Kit (agents, runners, sessions) |
| `google-genai` | Gemini model access |
| `requests` | HTTP calls to OpenWeatherMap |
| `python-dateutil` | Flexible date string parsing |
| `python-dotenv` | Load `.env` files |
| `langfuse` | Observability & tracing (optional) |

## License

MIT
