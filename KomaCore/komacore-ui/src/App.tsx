import { useState } from 'react';
import { ChevronRight, ChevronLeft, FileText, Shield, Calculator, TrendingUp, AlertCircle, Loader2, Check, Building, MapPin, DollarSign, Calendar, Info } from 'lucide-react';
import { Button } from './components/ui/Button';
import { Input } from './components/ui/Input';
import { Label } from './components/ui/Label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/Card';
import { BidPriceResults } from './components/BidPriceResults';
import axios from 'axios';
import type { BidPriceResponse } from './api/komacore';

// API Configuration
const api = axios.create({
  baseURL: (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': (import.meta as any).env?.VITE_API_KEY || 'dev'
  },
  timeout: 30000
});

// Axios interceptor for Korean error messages
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Convert network/CORS/HTTP/proxy errors to Korean hints
    if (!error.response) {
      // Network error (no response received)
      if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error')) {
        error.__hint = '백엔드 서버가 실행되지 않았습니다. npm run dev:all 또는 백엔드를 먼저 실행하세요.';
      } else if (error.code === 'ENOTFOUND') {
        error.__hint = 'API 서버 주소를 찾을 수 없습니다. 프록시 설정을 확인하세요.';
      } else if (error.message.includes('timeout')) {
        error.__hint = '요청 시간이 초과되었습니다. 백엔드 서버 상태를 확인하세요.';
      } else if (error.message.includes('ECONNRESET')) {
        error.__hint = '연결이 재설정되었습니다. 백엔드 서버를 다시 시작하세요.';
      } else {
        error.__hint = `네트워크/프록시 오류: ${error.message}`;
      }
    } else if (error.response.status === 0) {
      // CORS error (should not happen with proxy)
      error.__hint = 'CORS 정책 위반입니다. Vite 프록시 설정을 확인하세요.';
    } else if (error.response.status === 401) {
      error.__hint = 'API 키가 유효하지 않습니다. 인증 정보를 확인하세요.';
    } else if (error.response.status === 403) {
      error.__hint = '접근이 거부되었습니다. 권한을 확인하세요.';
    } else if (error.response.status === 404) {
      error.__hint = 'API 엔드포인트를 찾을 수 없습니다. 백엔드 라우팅을 확인하세요.';
    } else if (error.response.status === 500) {
      error.__hint = '서버 내부 오류가 발생했습니다. 백엔드 로그를 확인하세요.';
    } else if (error.response.status >= 400) {
      const detail = error.response.data?.detail || error.response.data?.message || '';
      error.__hint = `HTTP ${error.response.status}: ${detail || '서버 오류'}`;
    }
    
    return Promise.reject(error);
  }
);

// Types
interface OnbidParseResponse {
  status: string; // "ok" | "pending"
  requested_case?: string; // User input (original case_no or url)
  case_key?: string; // Normalized internal key for storage
  case_no?: string; // Display case_no (if extractable)
  source_hint?: string; // "url" | "case"
  mismatch: boolean; // True if requested_case != case_no/case_key
  asset_type?: string;
  use_type?: string;
  address?: string;
  areas: {
    building_m2?: number;
    land_m2?: number;
    land_right?: boolean;
  };
  appraisal?: number;
  min_bid?: number;
  round?: number;
  flags: {
    지분: boolean;
    대지권없음: boolean;
    건물만: boolean;
    부가세: boolean;
    특약: boolean;
  };
  attachment_state: string; // "READY" | "NONE" | "DOWNLOAD_FAIL"
  extracted_keys: number;
  error_code?: string;
  error_hint?: string; // Korean message for UI banners
}

interface AnalyzeResponse {
  risk_level: 'safe' | 'conditional' | 'risky';
  flags: string[];
  notes: string[];
}

interface BidPriceRequest {
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

function App() {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [mismatchWarning, setMismatchWarning] = useState<string | null>(null);

  // Step 1 data
  const [onbidUrl, setOnbidUrl] = useState('');
  const [caseNo, setCaseNo] = useState('');
  const [forceRefresh, setForceRefresh] = useState(false);
  const [propertyData, setPropertyData] = useState<OnbidParseResponse | null>(null);

  // Step 2 data  
  const [riskAnalysis, setRiskAnalysis] = useState<AnalyzeResponse | null>(null);

  // Step 3 data
  const [financialData, setFinancialData] = useState<BidPriceRequest>({
    appraisal_price: 0,
    market_avg_price: 0,
    expected_monthly_rent: 2000000,
    mgmt_cost: 200000,
    vacancy_rate: 0.05,
    repair_capex: 0.02,
    property_tax_est: 0.002,
    insurance_est: 0.001,
    interest_rate: 0.045,
    target_roi_base: 0.08,
    cash_cap: 150000000,
    est_loan_limit: 350000000
  });

  // Step 4 data
  const [bidResults, setBidResults] = useState<BidPriceResponse | null>(null);

  // API Functions
  const parseOnbidData = async () => {
    if (!onbidUrl && !caseNo) {
      setError('온비드 URL 또는 사건번호를 입력해주세요.');
      return;
    }

    setLoading(true);
    setError(null);
    setInfoMessage(null);
    setMismatchWarning(null);
    
    // Reset states when fetching new data (as requested)
    setPropertyData(null);
    setRiskAnalysis(null);
    setBidResults(null);

    try {
      const payload: any = {};
      if (onbidUrl) payload.url = onbidUrl;
      if (caseNo) payload.case = caseNo;  // Updated to use unified 'case' field
      if (forceRefresh) payload.force = true;

      const response = await api.post<OnbidParseResponse>('/onbid/parse', payload);
      const data = response.data;
      
      setPropertyData(data);
      
      // Handle mismatch detection
      if (data.mismatch) {
        setMismatchWarning(`입력 사건과 다른 사건이 감지됨 — 입력: ${data.requested_case} / 응답: ${data.case_no || data.case_key}`);
      }
      
      // Handle STRICT mode and error hints
      if (data.error_hint && !data.mismatch) {
        if (data.attachment_state === "NONE" && data.error_code === "ATTACHMENT_NONE") {
          // STRICT mode: Check if this is due to blocked mock data
          if (data.error_hint.includes('실제') || data.error_hint.includes('STRICT') || 
              data.error_hint.includes('Mock') || data.error_hint.includes('실제 데이터')) {
            setInfoMessage(`🔒 STRICT 모드: ${data.error_hint} | 가짜 데이터 생성이 차단되어 빈 응답을 반환합니다.`);
          } else {
            setInfoMessage(data.error_hint); // Standard yellow info banner  
          }
          setError(null);
        } else {
          setError(data.error_hint); // Red error banner
          setInfoMessage(null);
        }
      } else if (!data.mismatch) {
        setError(null);
        setInfoMessage(null);
      }
      
      // Pre-fill financial data
      setFinancialData(prev => ({
        ...prev,
        appraisal_price: data.appraisal || prev.appraisal_price,
        market_avg_price: data.min_bid ? data.min_bid * 1.1 : prev.market_avg_price
      }));

      setCurrentStep(2);
    } catch (err: any) {
      // Use Korean hint from interceptor if available, otherwise default message
      const errorMessage = err.__hint || '네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
      setError(errorMessage);
      setInfoMessage(null);
      setMismatchWarning(null);
    } finally {
      setLoading(false);
    }
  };

  const analyzeRisk = async () => {
    if (!propertyData) return;

    setLoading(true);
    setError(null);

    try {
      const payload = {
        asset_class: propertyData.asset_type,
        flags_input: {
          is_share_only: propertyData.flags.지분,
          has_land_right: propertyData.areas.land_right !== false,
          building_only: propertyData.flags.건물만,
          tenant_with_seniority: false,
          tax_arrears: false,
          special_terms: propertyData.flags.특약,
          vat_applicable: propertyData.flags.부가세,
          occupied: false,
          defects: false
        }
      };

      const response = await api.post<AnalyzeResponse>('/analyze', payload);
      setRiskAnalysis(response.data);
      setCurrentStep(3);
    } catch (err: any) {
      const errorMessage = err.__hint || err.response?.data?.detail || '권리분석 중 오류가 발생했습니다.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const calculateBidPrice = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.post<BidPriceResponse>('/bidprice', financialData);
      setBidResults(response.data);
      setCurrentStep(4);
    } catch (err: any) {
      const errorMessage = err.__hint || err.response?.data?.detail || '입찰가 계산 중 오류가 발생했습니다.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ko-KR').format(amount);
  };

  const formatPercent = (rate: number) => {
    return `${(rate * 100).toFixed(1)}%`;
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'safe': return 'text-green-600 bg-green-100 border-green-200';
      case 'conditional': return 'text-yellow-600 bg-yellow-100 border-yellow-200';
      case 'risky': return 'text-red-600 bg-red-100 border-red-200';
      default: return 'text-gray-600 bg-gray-100 border-gray-200';
    }
  };

  const getRiskText = (level: string) => {
    switch (level) {
      case 'safe': return '안전';
      case 'conditional': return '조건부';
      case 'risky': return '위험';
      default: return '미확인';
    }
  };

  const steps = [
    { id: 1, title: '물건 입력', icon: FileText },
    { id: 2, title: '권리분석', icon: Shield },  
    { id: 3, title: '시세조사', icon: Calculator },
    { id: 4, title: '입찰가', icon: TrendingUp }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">KomaCore 입찰가격 분석기</h1>
          <p className="text-gray-600 mt-2">한국 부동산 투자를 위한 4단계 위저드</p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => {
              const isActive = currentStep === step.id;
              const isCompleted = currentStep > step.id;
              const Icon = step.icon;
              
              return (
                <div key={step.id} className="flex items-center">
                  <div className={`flex items-center space-x-2 px-4 py-2 rounded-lg ${
                    isActive ? 'bg-blue-100 text-blue-700 font-medium' : 
                    isCompleted ? 'bg-green-100 text-green-700' : 'text-gray-500'
                  }`}>
                    <Icon className="h-5 w-5" />
                    <span>{step.title}</span>
                    {isCompleted && <Check className="h-4 w-4" />}
                  </div>
                  {index < steps.length - 1 && (
                    <ChevronRight className="h-5 w-5 text-gray-400 mx-2" />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Error Display */}
        {error && (
          <Card className="border-red-200 bg-red-50 mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-red-800">
                <AlertCircle className="h-5 w-5" />
                오류 발생
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-red-700">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Info Message Display */}
        {infoMessage && (
          <Card className="border-yellow-200 bg-yellow-50 mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-yellow-800">
                <Info className="h-5 w-5" />
                알림
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-yellow-700">{infoMessage}</p>
            </CardContent>
          </Card>
        )}

        {/* Mismatch Warning Display */}
        {mismatchWarning && (
          <Card className="border-orange-200 bg-orange-50 mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-orange-800">
                <AlertCircle className="h-5 w-5" />
                사건 불일치 감지
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-orange-700">{mismatchWarning}</p>
              <p className="text-orange-600 text-sm mt-2">강제 새로수집을 체크하여 다시 시도해보세요.</p>
            </CardContent>
          </Card>
        )}

        {/* Loading Display */}
        {loading && (
          <Card className="border-blue-200 bg-blue-50 mb-6">
            <CardContent className="flex items-center justify-center py-8">
              <div className="flex items-center gap-3">
                <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                <span className="text-blue-800 font-medium">
                  {currentStep === 1 && '공고문을 분석하고 있습니다...'}
                  {currentStep === 2 && '권리관계를 분석하고 있습니다...'}
                  {currentStep === 3 && '입찰가격을 계산하고 있습니다...'}
                </span>
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Current Step */}
          <div>
            {/* STEP 1: 물건 입력 */}
            {currentStep === 1 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-6 w-6" />
                    STEP 1: 물건 입력
                  </CardTitle>
                  <CardDescription>
                    온비드 공고문 URL 또는 사건번호를 입력하여 물건 정보를 불러옵니다.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <Label htmlFor="onbidUrl">온비드 URL</Label>
                    <Input
                      id="onbidUrl"
                      value={onbidUrl}
                      onChange={(e) => setOnbidUrl(e.target.value)}
                      placeholder="https://www.onbid.co.kr/auction/case/12345"
                    />
                    {propertyData?.source_hint === 'url' && propertyData?.requested_case && (
                      <div className="mt-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                        ✓ 입력: {propertyData.requested_case} → 응답: {propertyData.case_no || propertyData.case_key}
                      </div>
                    )}
                  </div>
                  
                  <div className="text-center text-gray-500">또는</div>
                  
                  <div>
                    <Label htmlFor="caseNo">사건번호</Label>
                    <Input
                      id="caseNo"
                      value={caseNo}
                      onChange={(e) => setCaseNo(e.target.value)}
                      placeholder="예: 2024-12345"
                    />
                    {propertyData?.source_hint === 'case' && propertyData?.requested_case && (
                      <div className="mt-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded">
                        ✓ 입력: {propertyData.requested_case} → 응답: {propertyData.case_no || propertyData.case_key}
                      </div>
                    )}
                  </div>

                  {/* Force Refresh Toggle */}
                  <div className="flex items-center space-x-2 bg-gray-50 p-3 rounded-lg">
                    <input
                      type="checkbox"
                      id="forceRefresh"
                      checked={forceRefresh}
                      onChange={(e) => setForceRefresh(e.target.checked)}
                      className="rounded"
                    />
                    <Label htmlFor="forceRefresh" className="text-sm">
                      강제 새로수집 (캐시 무시)
                    </Label>
                  </div>

                  <Button 
                    onClick={parseOnbidData}
                    className="w-full"
                    size="lg"
                    disabled={loading || (!onbidUrl && !caseNo)}
                  >
                    공고문 불러오기
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* STEP 2: 권리분석 */}
            {currentStep === 2 && propertyData && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-6 w-6" />
                    STEP 2: 권리분석
                  </CardTitle>
                  <CardDescription>
                    물건의 권리관계와 투자 위험도를 분석합니다.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    {Object.entries(propertyData.flags).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <span className="font-medium">{key}</span>
                        <span className={`px-2 py-1 rounded text-sm ${
                          value ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                        }`}>
                          {value ? '있음' : '없음'}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="flex gap-4">
                    <Button 
                      variant="outline" 
                      onClick={() => setCurrentStep(1)}
                      className="flex-1"
                    >
                      <ChevronLeft className="h-4 w-4 mr-2" />
                      이전
                    </Button>
                    <Button 
                      onClick={analyzeRisk}
                      className="flex-1"
                      disabled={loading}
                    >
                      안전등급 계산
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* STEP 3: 시세조사 */}
            {currentStep === 3 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calculator className="h-6 w-6" />
                    STEP 3: 시세조사
                  </CardTitle>
                  <CardDescription>
                    시세와 투자 조건을 입력합니다.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="appraisal">감정가 (원)</Label>
                      <Input
                        id="appraisal"
                        type="number"
                        value={financialData.appraisal_price}
                        onChange={(e) => setFinancialData(prev => ({ ...prev, appraisal_price: Number(e.target.value) }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="market">시세 (원)</Label>
                      <Input
                        id="market"
                        type="number"
                        value={financialData.market_avg_price}
                        onChange={(e) => setFinancialData(prev => ({ ...prev, market_avg_price: Number(e.target.value) }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="rent">월세 (원)</Label>
                      <Input
                        id="rent"
                        type="number"
                        value={financialData.expected_monthly_rent}
                        onChange={(e) => setFinancialData(prev => ({ ...prev, expected_monthly_rent: Number(e.target.value) }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="mgmt">관리비 (원)</Label>
                      <Input
                        id="mgmt"
                        type="number"
                        value={financialData.mgmt_cost}
                        onChange={(e) => setFinancialData(prev => ({ ...prev, mgmt_cost: Number(e.target.value) }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="vacancy">공실률 (%)</Label>
                      <Input
                        id="vacancy"
                        type="number"
                        step="0.01"
                        value={financialData.vacancy_rate * 100}
                        onChange={(e) => setFinancialData(prev => ({ ...prev, vacancy_rate: Number(e.target.value) / 100 }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="repair">수리비율 (%)</Label>
                      <Input
                        id="repair"
                        type="number"
                        step="0.01"
                        value={financialData.repair_capex * 100}
                        onChange={(e) => setFinancialData(prev => ({ ...prev, repair_capex: Number(e.target.value) / 100 }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="interest">대출금리 (%)</Label>
                      <Input
                        id="interest"
                        type="number"
                        step="0.01"
                        value={financialData.interest_rate * 100}
                        onChange={(e) => setFinancialData(prev => ({ ...prev, interest_rate: Number(e.target.value) / 100 }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="roi">목표수익률 (%)</Label>
                      <Input
                        id="roi"
                        type="number"
                        step="0.01"
                        value={financialData.target_roi_base * 100}
                        onChange={(e) => setFinancialData(prev => ({ ...prev, target_roi_base: Number(e.target.value) / 100 }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="cash">보유현금 (원)</Label>
                      <Input
                        id="cash"
                        type="number"
                        value={financialData.cash_cap}
                        onChange={(e) => setFinancialData(prev => ({ ...prev, cash_cap: Number(e.target.value) }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="loan">대출한도 (원)</Label>
                      <Input
                        id="loan"
                        type="number"
                        value={financialData.est_loan_limit}
                        onChange={(e) => setFinancialData(prev => ({ ...prev, est_loan_limit: Number(e.target.value) }))}
                      />
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <Button 
                      variant="outline" 
                      onClick={() => setCurrentStep(2)}
                      className="flex-1"
                    >
                      <ChevronLeft className="h-4 w-4 mr-2" />
                      이전
                    </Button>
                    <Button 
                      onClick={calculateBidPrice}
                      className="flex-1"
                      disabled={loading}
                    >
                      입찰가 계산
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* STEP 4: 입찰가 */}
            {currentStep === 4 && bidResults && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-6 w-6" />
                    STEP 4: 입찰가 결과
                  </CardTitle>
                  <CardDescription>
                    3가지 시나리오별 최적 입찰가격과 ROI를 확인하세요.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {bidResults.scenarios.map((scenario, index) => (
                      <div key={index} className="p-4 border rounded-lg bg-white">
                        <h3 className="font-bold text-lg mb-2">{scenario.name}</h3>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span>입찰가:</span>
                            <span className="font-medium">{formatCurrency(Math.round(scenario.bid_price))}원</span>
                          </div>
                          <div className="flex justify-between">
                            <span>월순익:</span>
                            <span className="font-medium">{formatCurrency(Math.round(scenario.monthly_net))}원</span>
                          </div>
                          <div className="flex justify-between">
                            <span>연수익률:</span>
                            <span className="font-medium text-green-600">{formatPercent(scenario.annual_roi)}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h3 className="font-bold text-blue-800 mb-2">권장 상한가</h3>
                    <div className="text-2xl font-bold text-blue-600">
                      {formatCurrency(Math.round(bidResults.affordable_bid.bid_price))}원
                    </div>
                    <div className="text-sm text-blue-600 mt-1">
                      {bidResults.affordable_bid.reason.join(', ')}
                    </div>
                  </div>

                  <Button 
                    variant="outline" 
                    onClick={() => setCurrentStep(3)}
                    className="w-full"
                  >
                    <ChevronLeft className="h-4 w-4 mr-2" />
                    시세조사로 돌아가기
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - Summary Info */}
          <div>
            {propertyData && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Building className="h-5 w-5" />
                    물건 정보
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-start gap-3">
                    <MapPin className="h-5 w-5 text-gray-500 mt-0.5" />
                    <div>
                      <div className="font-medium">{propertyData.use_type}</div>
                      <div className="text-sm text-gray-600">{propertyData.address}</div>
                    </div>
                  </div>
                  
                  {propertyData.appraisal && (
                    <div className="flex items-center gap-3">
                      <DollarSign className="h-5 w-5 text-gray-500" />
                      <div>
                        <div className="text-sm text-gray-600">감정가</div>
                        <div className="font-medium">{formatCurrency(propertyData.appraisal)}원</div>
                      </div>
                    </div>
                  )}
                  
                  {propertyData.min_bid && (
                    <div className="flex items-center gap-3">
                      <Calendar className="h-5 w-5 text-gray-500" />
                      <div>
                        <div className="text-sm text-gray-600">최저입찰가 ({propertyData.round}회차)</div>
                        <div className="font-medium">{formatCurrency(propertyData.min_bid)}원</div>
                      </div>
                    </div>
                  )}

                  <div className="flex flex-wrap gap-2 pt-2">
                    {Object.entries(propertyData.flags).map(([key, value]) => (
                      value && (
                        <span key={key} className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded">
                          {key}
                        </span>
                      )
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {riskAnalysis && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5" />
                    위험도 분석
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={`inline-flex items-center px-3 py-2 rounded-full text-sm font-medium border ${getRiskColor(riskAnalysis.risk_level)}`}>
                    <Info className="h-4 w-4 mr-2" />
                    {getRiskText(riskAnalysis.risk_level)}
                  </div>
                  {riskAnalysis.notes.length > 0 && (
                    <div className="mt-4">
                      <div className="text-sm font-medium text-gray-700 mb-2">주의사항:</div>
                      <ul className="text-sm text-gray-600 space-y-1">
                        {riskAnalysis.notes.map((note, index) => (
                          <li key={index} className="flex items-start gap-2">
                            <span className="text-yellow-500">•</span>
                            {note}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {bidResults && currentStep === 4 && (
              <div>
                <BidPriceResults results={bidResults} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;