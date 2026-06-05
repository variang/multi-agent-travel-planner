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

## Running the Planner

```bash
python main.py
```

This runs a set of example queries against the coordinator agent and prints the results to the terminal. You can edit `main.py` to supply your own destination, duration, and interests.

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
├── main.py                      # Entry point with example queries
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

## License

MIT
