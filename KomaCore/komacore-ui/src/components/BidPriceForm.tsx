import { useState } from 'react';
import { Calculator, TrendingUp, AlertCircle, Banknote } from 'lucide-react';
import { Button } from './ui/Button';
import { Input } from './ui/Input';
import { Label } from './ui/Label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/Card';
import { komacoreAPI, type BidPriceRequest, type BidPriceResponse } from '../api/komacore';
import { formatCurrency, formatPercent } from '../lib/utils';

interface BidPriceFormProps {
  onResults: (results: BidPriceResponse | null) => void;
  onLoading: (isLoading: boolean) => void;
  onError: (error: string | null) => void;
}

export function BidPriceForm({ onResults, onLoading, onError }: BidPriceFormProps) {
  const [formData, setFormData] = useState<BidPriceRequest>({
    appraisal_price: 500000000, // 5억
    market_avg_price: 480000000, // 4억8천만
    expected_monthly_rent: 2500000, // 250만원
    mgmt_cost: 200000, // 20만원
    vacancy_rate: 0.05, // 5%
    repair_capex: 0.02, // 2%
    property_tax_est: 0.002, // 0.2%
    insurance_est: 0.001, // 0.1%
    interest_rate: 0.045, // 4.5%
    target_roi_base: 0.08, // 8%
    cash_cap: 150000000, // 1억5천만
    est_loan_limit: 350000000 // 3억5천만
  });

  const handleInputChange = (field: keyof BidPriceRequest) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = parseFloat(e.target.value) || 0;
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    onError(null);
    onLoading(true);
    
    try {
      const results = await komacoreAPI.fetchBidPrice(formData);
      onResults(results);
    } catch (err: any) {
      console.error('API Error:', err);
      onError(err.response?.data?.detail || err.message || '분석 중 오류가 발생했습니다.');
      onResults(null);
    } finally {
      onLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-4xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calculator className="h-6 w-6" />
          입찰가격 분석기
        </CardTitle>
        <CardDescription>
          부동산 투자 정보를 입력하여 최적 입찰가격과 ROI 시나리오를 분석합니다.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 부동산 기본 정보 */}
          <div>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Banknote className="h-5 w-5" />
              부동산 기본 정보
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="appraisal_price">감정가격 (원)</Label>
                <Input
                  id="appraisal_price"
                  type="number"
                  step="1000000"
                  value={formData.appraisal_price}
                  onChange={handleInputChange('appraisal_price')}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="market_avg_price">시장 평균가격 (원)</Label>
                <Input
                  id="market_avg_price"
                  type="number"
                  step="1000000"
                  value={formData.market_avg_price}
                  onChange={handleInputChange('market_avg_price')}
                  required
                />
              </div>
            </div>
          </div>

          {/* 임대 수입 정보 */}
          <div>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              임대 수입 정보
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="expected_monthly_rent">예상 월임대료 (원)</Label>
                <Input
                  id="expected_monthly_rent"
                  type="number"
                  step="10000"
                  value={formData.expected_monthly_rent}
                  onChange={handleInputChange('expected_monthly_rent')}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="mgmt_cost">관리비 (원/월)</Label>
                <Input
                  id="mgmt_cost"
                  type="number"
                  step="10000"
                  value={formData.mgmt_cost}
                  onChange={handleInputChange('mgmt_cost')}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vacancy_rate">공실률 (%)</Label>
                <Input
                  id="vacancy_rate"
                  type="number"
                  step="0.01"
                  max="1"
                  value={formData.vacancy_rate * 100}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    vacancy_rate: parseFloat(e.target.value) / 100 || 0 
                  }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="repair_capex">수선충당금 (%)</Label>
                <Input
                  id="repair_capex"
                  type="number"
                  step="0.01"
                  max="1"
                  value={formData.repair_capex * 100}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    repair_capex: parseFloat(e.target.value) / 100 || 0 
                  }))}
                  required
                />
              </div>
            </div>
          </div>

          {/* 비용 및 세금 정보 */}
          <div>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              비용 및 세금 정보
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="property_tax_est">재산세율 (%)</Label>
                <Input
                  id="property_tax_est"
                  type="number"
                  step="0.001"
                  max="1"
                  value={formData.property_tax_est * 100}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    property_tax_est: parseFloat(e.target.value) / 100 || 0 
                  }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="insurance_est">보험료율 (%)</Label>
                <Input
                  id="insurance_est"
                  type="number"
                  step="0.001"
                  max="1"
                  value={formData.insurance_est * 100}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    insurance_est: parseFloat(e.target.value) / 100 || 0 
                  }))}
                  required
                />
              </div>
            </div>
          </div>

          {/* 투자 조건 */}
          <div>
            <h3 className="text-lg font-semibold mb-4">투자 조건</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="interest_rate">대출 금리 (%)</Label>
                <Input
                  id="interest_rate"
                  type="number"
                  step="0.01"
                  max="1"
                  value={formData.interest_rate * 100}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    interest_rate: parseFloat(e.target.value) / 100 || 0 
                  }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="target_roi_base">목표 ROI (%)</Label>
                <Input
                  id="target_roi_base"
                  type="number"
                  step="0.01"
                  max="1"
                  value={formData.target_roi_base * 100}
                  onChange={(e) => setFormData(prev => ({ 
                    ...prev, 
                    target_roi_base: parseFloat(e.target.value) / 100 || 0 
                  }))}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cash_cap">보유 현금 (원)</Label>
                <Input
                  id="cash_cap"
                  type="number"
                  step="1000000"
                  value={formData.cash_cap}
                  onChange={handleInputChange('cash_cap')}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="est_loan_limit">예상 대출한도 (원)</Label>
                <Input
                  id="est_loan_limit"
                  type="number"
                  step="1000000"
                  value={formData.est_loan_limit}
                  onChange={handleInputChange('est_loan_limit')}
                  required
                />
              </div>
            </div>
          </div>

          <div className="flex gap-4">
            <Button 
              type="button" 
              variant="outline" 
              className="flex-1" 
              size="lg"
              onClick={() => {
                // Load sample data for testing
                setFormData({
                  appraisal_price: 235000000,
                  market_avg_price: 220000000,
                  expected_monthly_rent: 1900000,
                  mgmt_cost: 250000,
                  vacancy_rate: 0.08,
                  repair_capex: 0.02,
                  property_tax_est: 0.002,
                  insurance_est: 0.001,
                  interest_rate: 0.064,
                  target_roi_base: 0.09,
                  cash_cap: 150000000,
                  est_loan_limit: 164500000
                });
              }}
            >
              샘플로 계산
            </Button>
            <Button type="submit" className="flex-1" size="lg">
              입찰가격 분석하기
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}