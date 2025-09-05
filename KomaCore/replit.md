# KomaCore - Korean Real Estate Investment Analysis API

## Overview

KomaCore is a comprehensive Korean real estate investment analysis platform consisting of a FastAPI backend service and a React TypeScript frontend dashboard. The system provides three core functionalities: financial profile assessment for loan capacity calculation, property risk analysis based on various asset flags, and bid price optimization with ROI scenarios. The platform serves as a decision-support tool for real estate investors by calculating investment limits, assessing property risks, and determining optimal bidding strategies based on financial constraints and target returns.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### API Design Pattern
The application follows a clean RESTful API architecture with FastAPI, implementing three main endpoints under the `/api/v1/` namespace. Each endpoint serves a specific aspect of real estate investment analysis, with clear separation of concerns between profile analysis, risk assessment, and bid optimization.

### Request/Response Structure
All endpoints use Pydantic models for request validation and response serialization, ensuring type safety and automatic API documentation. Each response includes a unique request ID (`req_id`) for tracking and debugging purposes. The system implements comprehensive input validation with appropriate field constraints (e.g., credit scores between 300-1000, income values >= 0).

### Financial Calculation Engine
The core business logic centers around Korean real estate financing rules, including DSR (Debt Service Ratio) calculations that differ between salaried employees (40% cap) and self-employed individuals (30% cap). The system applies stress testing with configurable floor rates and credit score adjustments to determine realistic loan limits.

### Risk Assessment Framework
Property risk evaluation uses a flag-based system that categorizes investments into three risk levels: "safe", "conditional", and "risky". The assessment considers property-specific factors like land rights, tenant seniority, tax arrears, and occupancy status, providing investors with clear risk indicators.

### Investment Simulation Model
The bid price optimization employs a sophisticated simulation engine that calculates total investment requirements, monthly cash flows, and annual ROI across multiple scenarios (conservative, primary, aggressive). The system uses binary search algorithms to find optimal bid prices that meet target ROI requirements while respecting loan limits and cash constraints.

### Security and Configuration
API security is implemented through a simple API key authentication mechanism using HTTP headers. Environment-based configuration management allows for easy adjustment of key parameters like DSR caps, stress rates, and LTV limits without code changes.

## External Dependencies

### Backend Dependencies
- **FastAPI**: Modern Python web framework providing automatic API documentation, request validation, and async support
- **Pydantic**: Data validation and serialization library for type-safe request/response models
- **Uvicorn**: ASGI server for running the FastAPI application
- **python-dotenv**: Environment variable management for configuration settings
- **slowapi**: Rate limiting middleware for API protection
- **CORS Middleware**: Cross-origin resource sharing support for frontend integration

### Frontend Dependencies
- **React 19**: Modern frontend framework with TypeScript support
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework for styling
- **Recharts**: Chart visualization library for ROI and scenario display
- **Radix UI**: Accessible UI component primitives
- **Axios**: HTTP client for API communication
- **Lucide React**: Icon library for consistent UI elements
- **Framer Motion**: Animation library for smooth user interactions

The application architecture separates concerns between a robust backend API and an interactive frontend dashboard, ensuring scalability and maintainability while providing an excellent user experience.

## Test Execution

### Running Tests

To run the automated regression tests:

```bash
# Quick test run
make test

# Run tests with coverage report
make coverage

# Manual pytest execution
PYTHONPATH=. pytest -q --maxfail=1 --disable-warnings
```

### Test Coverage

The test suite includes:
- Health check endpoint validation
- Profile analysis with DSR calculations
- Property risk assessment with flag evaluation
- Bid price optimization with ROI scenarios

Current test coverage: 86% (10/10 tests passing)

### Frontend Development

The React frontend is located in the `komacore-ui/` directory:

```bash
cd komacore-ui

# Install dependencies
npm install

# Start development server (runs on port 5173)
npm run dev

# Build for production
npm run build
```

The frontend includes:
- Comprehensive bid price analysis form with Korean language interface
- Real-time ROI calculations and scenario comparisons
- Interactive charts and data visualizations
- Responsive design for desktop and mobile devices
- Integration with the FastAPI backend via REST APIs

### API Testing

For manual API testing, refer to `docs/curl.md` for complete cURL examples for all endpoints.