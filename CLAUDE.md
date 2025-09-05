# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Backend (Python FastAPI)
```bash
# Navigate to KomaCore directory first
cd KomaCore

# Run tests
make test
# Alternative: PYTHONPATH=. pytest -q --maxfail=1 --disable-warnings

# Run tests with coverage
make coverage
# Alternative: PYTHONPATH=. pytest --cov=.

# Format code
make fmt
# Alternative: black . && ruff check --fix

# Lint code
make lint
# Alternative: ruff check && black --check .

# Start backend server
uvicorn main:app --host 0.0.0.0 --port 8000

# Development with auto-reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (React TypeScript)
```bash
# Navigate to UI directory
cd KomaCore/komacore-ui

# Install dependencies
npm install

# Start development server
npm run dev
# Runs on http://localhost:5173

# Build for production
npm run build

# Lint frontend code
npm run lint

# Run both backend and frontend concurrently
npm run dev:all
```

### Full Stack Development
```bash
# From KomaCore/komacore-ui directory
npm run dev:all
# Starts both FastAPI backend (port 8000) and React frontend (port 5173)
```

## High-Level Architecture

### Core System Overview
KomaCore is a Korean real estate investment analysis platform with two main components:
- **Backend**: Python FastAPI service providing financial analysis APIs
- **Frontend**: React TypeScript dashboard with Tailwind CSS

### Backend Architecture (KomaCore/)

#### Main Components
- `main.py`: FastAPI application with three core endpoints
- `models.py`: Pydantic data models for request/response validation
- `onbid_parser.py`: Korean auction site (onbid) data extraction engine
- `utils.py`: Financial calculation utilities (DSR, ROI, investment simulation)

#### API Endpoints Structure
All business endpoints require `x-api-key` header authentication:
- `POST /api/v1/profile`: Financial profile analysis for loan capacity
- `POST /api/v1/analyze`: Property risk assessment based on asset flags  
- `POST /api/v1/bidprice`: Bid price optimization with ROI scenarios
- `POST /api/v1/onbid/parse`: Korean auction case data extraction

Public endpoints (no auth required):
- `GET /api/v1/healthz`: Health check
- `GET /api/v1/meta`: System metadata

#### Key Business Logic
- **DSR Calculation**: Different debt-service ratios for salaried (40%) vs self-employed (30%)
- **Risk Assessment**: Flag-based system categorizing properties as safe/conditional/risky
- **Investment Simulation**: Binary search optimization for bid prices meeting target ROI
- **Korean Auction Parsing**: Regex-based extraction of property flags (지분, 대지권없음, 건물만, etc.)

#### Data Storage Patterns
- Environment-based configuration (`.env.dev`, `.env.prod`)
- Case data cached in `data/cache/case_*/latest.json`
- Raw auction data stored in `data/raw/{case_no}/`
- Attachments saved alongside case data

### Frontend Architecture (KomaCore/komacore-ui/)

#### Tech Stack
- React 19 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Recharts for data visualization
- Framer Motion for animations
- Radix UI components

#### Key Features
- **실시간 계산**: Real-time ROI calculations with three scenarios (보수/주력/공격)
- **반응형 디자인**: Mobile-friendly responsive design
- **API 통합**: Axios-based communication with FastAPI backend
- **차트 시각화**: Interactive investment scenario charts

### Development Environment Configuration

#### Environment Files
- Backend: `.env.dev`, `.env.prod` in `KomaCore/`
- Frontend: `.env`, `.env.local` in `KomaCore/komacore-ui/`
- API key for development: `x-api-key: dev`

#### Port Configuration
- Backend API: `localhost:8000`
- Frontend Dev Server: `localhost:5173`
- Production Preview: `localhost:5000`

#### CORS Configuration
Configured for local development domains:
- `localhost:3000`, `localhost:5173`, `localhost:5000`

### Testing Strategy

#### Backend Testing
- **Unit Tests**: `tests/test_api.py`, `tests/test_ops.py`
- **Integration Tests**: `tests/test_onbid_parse.py` 
- **Regression Tests**: `tests/test_strict_mode_regression.py`
- **Coverage Reports**: Available via `make coverage`

#### Code Quality Tools
- **Python**: Black formatting + Ruff linting
- **TypeScript**: ESLint for frontend code
- **Type Checking**: TypeScript compiler for frontend

### Key Dependencies

#### Backend Critical Dependencies
- `fastapi`: Web framework
- `pydantic`: Data validation and serialization
- `beautifulsoup4` + `lxml`: HTML parsing for auction data
- `requests` + `httpx`: HTTP client libraries
- `slowapi`: Rate limiting
- `python-dotenv`: Environment configuration

#### Frontend Critical Dependencies  
- `react` + `react-dom`: UI framework
- `axios`: HTTP client for API communication
- `recharts`: Chart visualization library
- `tailwindcss`: Utility-first CSS framework
- `framer-motion`: Animation library

### Special Considerations

#### Korean Language Support
The system handles Korean text processing for:
- Auction site data extraction with Korean regex patterns
- Property type classification in Korean
- Error messages in Korean for user-facing responses

#### Financial Domain Logic
- Implements Korean real estate financing rules
- DSR calculations specific to Korean banking regulations  
- Property risk assessment based on Korean auction system flags
- Investment simulation using Korean market assumptions