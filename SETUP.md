# WakeWander 🌍✈️

> AI-Powered Travel Planner with Multi-Step Reasoning using LangGraph

WakeWander is an intelligent travel planning assistant that uses Plan-and-Execute architecture to break down complex travel planning into structured, manageable steps. Built with LangGraph for stateful orchestration and Gemini 2.5 Flash for natural language understanding.

## ✨ Features

- 🤖 **Multi-Step AI Planning**: 8 node LangGraph workflow for structured itinerary generation
- 🔄 **Human-in-the-Loop**: Interactive interrupts for missing information and destination selection
- 🌦️ **Season-Aware Planning**: Intelligent recommendations based on travel season
- 💰 **Budget Tracking**: Real-time budget allocation and cost breakdown
- 📊 **Progress Streaming**: Live updates via Server-Sent Events (SSE)
- 💾 **State Persistence**: Conversation history and itinerary storage

## 🏗️ Architecture
```
Frontend (Next.js + React)
    ↓ SSE Streaming
Backend (FastAPI + Python)
    ↓ LangGraph Orchestration
LLM (Gemini 2.5 Flash)
    ↓ State Management
Database (Supabase PostgreSQL)
```

## 📋 Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Google API Key** (Gemini)
- **Supabase Account** (free tier)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/wakewander.git
cd wakewander
```

### 2. Backend Setup
```bash
cd WakeWander-backend

# Create virtual environment
python -m venv wakewander_venv
source wakewander_venv/bin/activate  # On Windows: wakewander_venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
Copy provided env example to .env

# Run backend
uvicorn app.main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`

### 3. Frontend Setup
```bash
cd ../WakeWander-frontend

# Install dependencies
npm install

# Create .env.local file
Copy provided env example to .env.local

# Run frontend
npm run dev
```

Frontend will be available at `http://localhost:3000`

### 4. Database Setup

**Supabase Tables:**

Run these SQL commands in Supabase SQL Editor (One-Time):
```sql
-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    messages JSONB DEFAULT '[]'::jsonb,
    state JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Itineraries table
CREATE TABLE itineraries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id),
    destination TEXT NOT NULL,
    duration_days INTEGER NOT NULL,
    budget NUMERIC(10, 2) NOT NULL,
    season TEXT,
    travel_dates TEXT,
    plan JSONB NOT NULL,
    budget_allocation JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_conversations_created ON conversations(created_at DESC);
CREATE INDEX idx_itineraries_conversation ON itineraries(conversation_id);
```

## 🔑 API Keys

### Google Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Get API key and add to backend `.env` file

### Supabase Credentials

1. Go to [Supabase] and create account
2. Create new project with Postgres and get DB link
3. Add to backend `.env` file

## 📁 Project Structure
```
wakewander/
├── WakeWander-backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── graph.py           # LangGraph workflow definition
│   │   │   ├── node_utilities.py  # Node implementations
│   │   │   └── state.py           # State schema
│   │   ├── api/
│   │   │   └── routes.py          # FastAPI endpoints
│   │   ├── core/
│   │   │   └── database.py        # Supabase connection
│   │   ├── models/
│   │   │   └── models.py          # SQLAlchemy models
│   │   └── main.py                # FastAPI app
│   └── requirements.txt
├── WakeWander-frontend/
│   ├── src/
│   │   ├── app/
│   │   │   └── page.tsx           # Main UI component
│   │   └── lib/
│   │       └── api.ts             # API client
│   ├── package.json
│   └── next.config.js
└── README.md
```

## 🎯 Usage

### Basic Example

1. Start both backend and frontend
2. Open `http://localhost:3000`
3. Enter a travel request:
```
   "Plan a 5-day summer trip with $3000 budget"
```
4. Follow the interactive prompts
5. Receive complete itinerary with budget breakdown

## 🛠️ Technology Stack

### Backend
- **Python 3.11** - Core language
- **FastAPI** - Async web framework
- **LangGraph** - Agentic workflow orchestration
- **LangChain** - LLM utilities
- **Gemini 2.5 Flash** - Language model
- **Pydantic** - Data validation
- **SQLAlchemy** - ORM
- **sse-starlette** - Server-Sent Events

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **EventSource API** - SSE client

### Database
- **Supabase** - PostgreSQL hosting
- **PostgreSQL** - Relational database

## 🐛 Troubleshooting

**"GOOGLE_API_KEY not found"**
- Verify `.env` file exists in `WakeWander-backend/`
- Check key is valid at Google AI Studio

**"Connection to Supabase failed"**
- Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Check Supabase project is active
- Ensure tables are created (see Database Setup)

### Frontend Issues

**"Failed to fetch from API"**
- Verify backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Ensure CORS is enabled in FastAPI

**"EventSource connection failed"**
- Check SSE endpoint: `http://localhost:8000/api/chat/stream`
- Verify backend logs for errors

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

### Tools & Frameworks
- **[LangGraph](https://github.com/langchain-ai/langgraph)** - LangChain team for the stateful workflow framework that made multi-step orchestration possible
- **Gemini API** - Google for providing fast, cost-effective LLM access
- **[Supabase](https://supabase.com)** - For free PostgreSQL hosting and real-time capabilities
- **FastAPI** - Sebastián Ramírez for the excellent async Python framework

### AI Assistance
- **Claude (Anthropic)** - For frontend scaffolding, debugging assistance, and code review throughout development
- Invaluable help with SSE integration, state management patterns, and JSON parsing solutions
**Built with using LangGraph and Gemini AI**

### Research & Inspiration
- **ReAct Paper** - Yao et al. (2023) for the foundational reasoning + acting paradigm
- **Plan-and-Execute Pattern** - LangChain documentation and community examples
- **SagaLLM** - Chang & Geng (2025) for insights on multi-agent LLM planning
