# tests/test_api.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
API = "/api/v1"
HEAD = {"x-api-key": "dev"}

def test_healthz():
    r = client.get(f"{API}/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_profile():
    payload = {
        "job": "직장인",
        "annual_income": 78000000,
        "credit_score": 820,
        "existing_debt_principal": 0,
        "existing_debt_monthly_payment": 800000,
        "desired_ltv": 70,
        "cash_on_hand": 50000000
    }
    r = client.post(f"{API}/profile", json=payload, headers=HEAD)
    assert r.status_code == 200
    body = r.json()
    assert "est_loan_limit" in body
    assert isinstance(body["est_loan_limit"], int)

def test_analyze():
    payload = {
        "asset_class": "압류재산",
        "flags_input": {
            "is_share_only": False,
            "has_land_right": True,
            "building_only": False,
            "tenant_with_seniority": True,
            "tax_arrears": False,
            "special_terms": False,
            "vat_applicable": False,
            "occupied": False,
            "defects": False
        }
    }
    r = client.post(f"{API}/analyze", json=payload, headers=HEAD)
    assert r.status_code == 200
    body = r.json()
    assert "risk_level" in body
    assert body["risk_level"] in ("safe", "conditional", "risky")

def test_bidprice():
    payload = {
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
    }
    r = client.post(f"{API}/bidprice", json=payload, headers=HEAD)
    assert r.status_code == 200
    body = r.json()
    assert "scenarios" in body
    assert "affordable_bid" in body
    assert len(body["scenarios"]) == 3