import axios from 'axios';

export interface BidPriceRequest {
  appraisal_price: number;
  market_avg_price: number;
  expected_monthly_rent: number;
  mgmt_cost: number;
  vacancy_rate: number;
  repair_capex: number;
  property_tax_est: number;
  insurance_est: number;
  interest_rate: number;
  target_roi_base: number;
  cash_cap: number;
  est_loan_limit: number;
}

export interface ScenarioResult {
  name: string;
  bid_price: number;
  loan_amount: number;
  total_in: number;
  monthly_net: number;
  annual_roi: number;
}

export interface AffordableBid {
  bid_price: number;
  reason: string[];
}

export interface BidPriceResponse {
  scenarios: ScenarioResult[];
  affordable_bid: AffordableBid;
  req_id: string;
}

// Create axios instance with base configuration
const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': (import.meta as any).env?.VITE_API_KEY || 'dev'
  },
  timeout: 30000
});

// API functions
export const komacoreAPI = {
  fetchBidPrice: async (payload: BidPriceRequest): Promise<BidPriceResponse> => {
    const response = await api.post<BidPriceResponse>('/bidprice', payload);
    return response.data;
  },

  healthCheck: async () => {
    const response = await api.get('/healthz');
    return response.data;
  },

  getMeta: async () => {
    const response = await api.get('/meta');
    return response.data;
  }
};

export default komacoreAPI;