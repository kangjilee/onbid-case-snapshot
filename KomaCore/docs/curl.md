# KomaCore API cURL Examples

## Health Check
```bash
curl -X GET "http://localhost:8000/api/v1/healthz"
```

## Profile Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/profile" \
  -H "x-api-key: dev" \
  -H "Content-Type: application/json" \
  -d '{
    "job": "직장인",
    "annual_income": 78000000,
    "credit_score": 820,
    "existing_debt_principal": 0,
    "existing_debt_monthly_payment": 800000,
    "desired_ltv": 70,
    "cash_on_hand": 50000000
  }'
```

## Property Risk Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
  -H "x-api-key: dev" \
  -H "Content-Type: application/json" \
  -d '{
    "asset_class": "압류재산",
    "flags_input": {
      "is_share_only": false,
      "has_land_right": true,
      "building_only": false,
      "tenant_with_seniority": true,
      "tax_arrears": false,
      "special_terms": false,
      "vat_applicable": false,
      "occupied": false,
      "defects": false
    }
  }'
```

## Bid Price Optimization
```bash
curl -X POST "http://localhost:8000/api/v1/bidprice" \
  -H "x-api-key: dev" \
  -H "Content-Type: application/json" \
  -d '{
    "appraisal_price": 235000000,
    "market_avg_price": 220000000,
    "expected_monthly_rent": 1900000,
    "mgmt_cost": 250000,
    "vacancy_rate": 0.08,
    "repair_capex": 12000000,
    "property_tax_est": 2800000,
    "insurance_est": 300000,
    "interest_rate": 0.064,
    "target_roi_base": 0.09,
    "cash_cap": 50000000,
    "est_loan_limit": 339428571
  }'
```