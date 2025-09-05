# KomaCore UI - React Frontend

Korean real estate investment analysis dashboard built with React, TypeScript, and Tailwind CSS.

## Features

- **입찰가격 분석기**: Comprehensive bid price analysis tool
- **3가지 시나리오**: Conservative, primary, and aggressive investment scenarios
- **실시간 ROI 계산**: Real-time return on investment calculations
- **반응형 디자인**: Mobile-friendly responsive design
- **차트 시각화**: Interactive charts using Recharts

## Quick Start

### Prerequisites
- Node.js 20 or higher
- KomaCore FastAPI backend running on port 8000

### Installation & Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The development server runs on http://localhost:5173 by default.

### Environment Configuration

Copy `.env.sample` to `.env` and configure:

```bash
# Backend API configuration
VITE_API_BASE=http://localhost:8000/api/v1
VITE_API_KEY=dev
```

For production deployment, update these values accordingly.

## Architecture

### Core Components

- **BidPriceForm**: Main input form for real estate investment data
- **BidPriceResults**: Results display with charts and scenario cards
- **UI Components**: Custom UI components built with Radix UI and Tailwind CSS

### API Integration

The frontend communicates with the KomaCore FastAPI backend via:

- `/api/v1/bidprice` - Bid price analysis endpoint
- `/api/v1/healthz` - Health check endpoint
- `/api/v1/meta` - API metadata endpoint

### Technology Stack

- **React 19** - Frontend framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Recharts** - Chart visualization library
- **Radix UI** - Accessible UI components
- **Axios** - HTTP client for API requests
- **Lucide React** - Icon library

## Project Structure

```
komacore-ui/
├── src/
│   ├── components/
│   │   ├── ui/              # Reusable UI components
│   │   ├── BidPriceForm.tsx # Main input form
│   │   └── BidPriceResults.tsx # Results display
│   ├── api/
│   │   └── komacore.ts      # API client
│   ├── lib/
│   │   └── utils.ts         # Utility functions
│   ├── App.tsx              # Main application component
│   └── main.tsx             # Application entry point
├── public/                  # Static assets
├── .env                     # Environment variables
└── package.json            # Dependencies and scripts
```

## Usage Guide

1. **Enter Property Information**: Fill in the basic property details including appraisal price and market average price
2. **Set Rental Income**: Input expected monthly rent, management costs, vacancy rate, and repair reserves
3. **Configure Costs**: Set property tax rate, insurance rate, and other expenses
4. **Investment Conditions**: Specify loan interest rate, target ROI, available cash, and estimated loan limit
5. **Analyze**: Click the analysis button to get detailed bid price scenarios

The system will display:
- **Recommended Bid Price**: Optimal bid considering your constraints
- **Scenario Comparison**: Charts comparing 3 different investment approaches
- **Detailed Cards**: Individual scenario analysis with ROI calculations
- **Important Notes**: Key considerations for your investment decision

## Development

### Code Style
- TypeScript for type safety
- ESLint for code linting
- Consistent component patterns
- Korean language UI for target market

### Building & Deployment
```bash
# Development build
npm run build

# Production build (optimized)
npm run build -- --mode production
```

The built files will be in the `dist/` directory ready for deployment to any static hosting service.

## Integration with Backend

The frontend expects the KomaCore FastAPI backend to be running and accessible. Ensure:

1. Backend is running on the configured `VITE_API_BASE` URL
2. API key matches between frontend (`VITE_API_KEY`) and backend
3. CORS is properly configured on the backend to allow frontend domain

## License

Part of the KomaCore real estate investment analysis platform.