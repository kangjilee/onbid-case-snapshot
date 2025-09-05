import { TrendingUp, DollarSign, PieChart, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/Card';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { formatCurrency, formatPercent } from '../lib/utils';
import type { BidPriceResponse } from '../api/komacore';

interface BidPriceResultsProps {
  results: BidPriceResponse;
}

export function BidPriceResults({ results }: BidPriceResultsProps) {
  const { scenarios, affordable_bid } = results;

  // Prepare chart data
  const chartData = scenarios.map(scenario => ({
    name: scenario.name,
    입찰가격: Math.round(scenario.bid_price / 1000000), // 백만원 단위
    연간수익률: scenario.annual_roi * 100,
    월순수익: Math.round(scenario.monthly_net / 10000) // 만원 단위
  }));

  // Get scenario colors
  const getScenarioColor = (name: string) => {
    switch (name) {
      case '보수적': return '#ef4444'; // red
      case '주력': return '#3b82f6'; // blue
      case '공격적': return '#10b981'; // green
      default: return '#6b7280'; // gray
    }
  };

  return (
    <div className="space-y-6">
      {/* 권장 입찰가격 */}
      <Card className="border-green-200 bg-green-50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-green-800">
            <TrendingUp className="h-5 w-5" />
            권장 입찰가격
          </CardTitle>
          <CardDescription className="text-green-600">
            현금 보유액과 대출 한도를 고려한 최적 입찰가격
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-green-800 mb-2">
            {formatCurrency(affordable_bid.bid_price)}
          </div>
          {affordable_bid.reason.length > 0 && (
            <div className="space-y-1">
              <p className="text-sm text-green-700 font-medium">제한 요인:</p>
              <ul className="text-sm text-green-600 list-disc list-inside space-y-1">
                {affordable_bid.reason.map((reason, index) => (
                  <li key={index}>{reason}</li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 시나리오 비교 차트 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChart className="h-5 w-5" />
            시나리오별 분석 결과
          </CardTitle>
          <CardDescription>
            보수적, 주력, 공격적 시나리오의 입찰가격과 수익률 비교
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis yAxisId="left" orientation="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip 
                  formatter={(value, name) => {
                    if (name === '입찰가격') return [`${value}백만원`, '입찰가격'];
                    if (name === '연간수익률') return [`${value.toFixed(1)}%`, '연간 ROI'];
                    if (name === '월순수익') return [`${value}만원`, '월순수익'];
                    return [value, name];
                  }}
                  labelFormatter={(label) => `${label} 시나리오`}
                />
                <Bar yAxisId="left" dataKey="입찰가격" fill="#3b82f6" name="입찰가격" />
                <Bar yAxisId="right" dataKey="연간수익률" fill="#10b981" name="연간수익률" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* 시나리오별 상세 정보 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {scenarios.map((scenario, index) => {
          const color = getScenarioColor(scenario.name);
          const isRecommended = scenario.bid_price === affordable_bid.bid_price;

          return (
            <Card 
              key={index} 
              className={`relative ${isRecommended ? 'ring-2 ring-green-400 bg-green-50' : ''}`}
            >
              {isRecommended && (
                <div className="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full">
                  추천
                </div>
              )}
              <CardHeader className="pb-3">
                <CardTitle 
                  className="text-lg flex items-center gap-2"
                  style={{ color }}
                >
                  <DollarSign className="h-5 w-5" />
                  {scenario.name} 시나리오
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-muted-foreground">입찰가격</p>
                    <p className="font-semibold">
                      {formatCurrency(scenario.bid_price)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">대출액</p>
                    <p className="font-semibold">
                      {formatCurrency(scenario.loan_amount)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">총투자금</p>
                    <p className="font-semibold">
                      {formatCurrency(scenario.total_in)}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">월순수익</p>
                    <p className="font-semibold">
                      {formatCurrency(scenario.monthly_net)}
                    </p>
                  </div>
                </div>
                <div className="border-t pt-3">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">연간 ROI</span>
                    <span 
                      className="text-xl font-bold"
                      style={{ color }}
                    >
                      {formatPercent(scenario.annual_roi)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* 주의사항 */}
      <Card className="border-yellow-200 bg-yellow-50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-yellow-800">
            <AlertTriangle className="h-5 w-5" />
            분석 결과 주의사항
          </CardTitle>
        </CardHeader>
        <CardContent className="text-yellow-700 space-y-2">
          <ul className="list-disc list-inside space-y-1 text-sm">
            <li>이 분석은 입력하신 조건을 기반으로 한 예상 수치입니다.</li>
            <li>실제 투자 시에는 시장 상황, 법규 변경, 금리 변동 등을 추가로 고려해야 합니다.</li>
            <li>부동산 투자에는 항상 위험이 따르므로, 전문가와 상담 후 결정하시기 바랍니다.</li>
            <li>대출 조건과 세율은 개인 신용도와 정책에 따라 달라질 수 있습니다.</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}