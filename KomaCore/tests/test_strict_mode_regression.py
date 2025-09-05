"""
STRICT Mode Golden Set Regression Tests
=====================================

This test suite validates that STRICT mode functionality works correctly
and consistently blocks all mock/fake data generation while properly
handling real data parsing scenarios.

Test Coverage:
- STRICT mode environment variable detection
- Mock data generation blocking
- Cache isolation and contamination prevention  
- Error handling with empty data responses
- Debug endpoint functionality
- Real vs fake data differentiation
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from onbid_parser import OnbidParser
from models import OnbidParseRequest, OnbidParseResponse

class TestStrictModeRegression:
    """Golden set regression tests for STRICT mode functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
        self.api_headers = {"x-api-key": "dev"}
        self.api_base = "/api/v1"
        
    def test_strict_mode_environment_detection(self):
        """Test that STRICT mode is properly detected from environment"""
        # Test debug status endpoint shows STRICT mode state
        response = self.client.get(f"{self.api_base}/debug/status", headers=self.api_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "strict_mode" in data
        assert "enabled" in data["strict_mode"]
        assert "description" in data["strict_mode"]
        assert "STRICT mode blocks all mock/fake data generation" in data["strict_mode"]["description"]
    
    def test_strict_mode_blocks_mock_data(self):
        """Test that STRICT mode returns empty data instead of generating mock content"""
        # Test with a case number that would trigger mock generation in non-strict mode
        payload = {
            "case_no": "2024-99999-999",  # Non-existent case
            "force": True
        }
        
        response = self.client.post(f"{self.api_base}/onbid/parse", json=payload, headers=self.api_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # In STRICT mode, should return empty/null data rather than mock data
        assert data["status"] == "pending"
        assert data["asset_type"] is None
        assert data["use_type"] is None  
        assert data["address"] is None
        assert data["appraisal"] is None
        assert data["min_bid"] is None
        
        # Should have appropriate error code indicating no real data found
        assert data["error_code"] in ["ATTACHMENT_NONE", "REMOTE_HTTP_ERROR", "PARSE_EMPTY"]
    
    def test_cache_isolation_prevents_contamination(self):
        """Test that STRICT mode cache validation works correctly"""
        # Test cache debug endpoint
        response = self.client.get(f"{self.api_base}/debug/cache", headers=self.api_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert "cache_info" in data
        assert "strict_mode_validation" in data
        assert "STRICT mode ignores non-strict cache entries" in data["strict_mode_validation"]
        
        # Verify cache stats structure
        cache_info = data["cache_info"]
        assert "total_entries" in cache_info
        assert "strict_mode_entries" in cache_info
        assert "contaminated_entries" in cache_info
        assert isinstance(cache_info["total_entries"], int)
        assert isinstance(cache_info["strict_mode_entries"], int)
        assert isinstance(cache_info["contaminated_entries"], int)
    
    def test_strict_mode_real_data_processing(self):
        """Test that STRICT mode still attempts real data parsing"""
        # Test with a case that should attempt real parsing
        payload = {
            "case_no": "2024-01774-006",  # Known case number format
            "force": True
        }
        
        response = self.client.post(f"{self.api_base}/onbid/parse", json=payload, headers=self.api_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Should attempt real parsing (status should be "pending" if real data not found)
        assert data["status"] in ["ok", "pending"]
        assert "case_no" in data
        assert "req_id" in data
        
        # Should NOT generate fake data even if real parsing fails
        if data["status"] == "pending" and data["error_code"] == "ATTACHMENT_NONE":
            # This is correct STRICT mode behavior - real parsing attempted but no fake fallback
            assert data["asset_type"] is None
            assert data["use_type"] is None
    
    def test_error_handling_consistency(self):
        """Test that error handling is consistent in STRICT mode"""
        test_cases = [
            {"case_no": "invalid-format"},  # Invalid format
            {"case_no": "2024-99999-999"}, # Non-existent case
            {"url": "https://invalid-domain.test"}, # Invalid URL
        ]
        
        for payload in test_cases:
            payload["force"] = True
            response = self.client.post(f"{self.api_base}/onbid/parse", json=payload, headers=self.api_headers)
            assert response.status_code == 200, f"Failed for payload: {payload}"
            
            data = response.json()
            # All should return valid response structure without mock data
            assert "status" in data
            assert "error_code" in data
            assert data["status"] in ["ok", "pending"]
            
            # No mock data should be present
            if data["error_code"] in ["ATTACHMENT_NONE", "PARSE_EMPTY", "INVALID_INPUT"]:
                assert data["asset_type"] is None
                assert data["use_type"] is None
    
    def test_debug_endpoints_accessibility(self):
        """Test that debug endpoints are accessible and provide useful information"""
        # Test status endpoint
        status_response = self.client.get(f"{self.api_base}/debug/status", headers=self.api_headers)
        assert status_response.status_code == 200
        
        status_data = status_response.json()
        required_fields = ["status", "timestamp", "app_version", "environment", "strict_mode", "uptime_seconds"]
        for field in required_fields:
            assert field in status_data, f"Missing field: {field}"
        
        # Test cache endpoint  
        cache_response = self.client.get(f"{self.api_base}/debug/cache", headers=self.api_headers)
        assert cache_response.status_code == 200
        
        cache_data = cache_response.json()
        required_fields = ["status", "cache_directory", "cache_info", "strict_mode_validation"]
        for field in required_fields:
            assert field in cache_data, f"Missing field: {field}"
    
    def test_strict_mode_parser_initialization(self):
        """Test that OnbidParser correctly initializes in STRICT mode"""
        # This tests the parser's internal STRICT mode detection
        with patch.dict(os.environ, {"SCRAPER_STRICT": "true"}):
            parser = OnbidParser()
            assert parser.strict_mode == True
        
        with patch.dict(os.environ, {"SCRAPER_STRICT": "false"}):
            parser = OnbidParser()
            assert parser.strict_mode == False
        
        # Test default behavior (should be True)
        with patch.dict(os.environ, {}, clear=True):
            parser = OnbidParser()
            assert parser.strict_mode == True  # Default is strict
    
    def test_no_mock_generation_functions_accessible(self):
        """Test that mock generation functions are completely removed"""
        parser = OnbidParser()
        
        # These functions should not exist anymore
        mock_functions = [
            "_generate_mock_content",
            "_generate_mock_data", 
            "_create_mock_response",
            "_get_mock_property_data"
        ]
        
        for func_name in mock_functions:
            assert not hasattr(parser, func_name), f"Mock function {func_name} still exists!"
    
    def test_end_to_end_strict_workflow(self):
        """End-to-end test of complete STRICT mode workflow"""
        # 1. Verify STRICT mode is active
        status_response = self.client.get(f"{self.api_base}/debug/status", headers=self.api_headers)
        assert status_response.json()["strict_mode"]["enabled"] == True
        
        # 2. Test parsing request that would generate mock data in non-strict mode
        parse_payload = {"case_no": "2024-12345-001", "force": True}
        parse_response = self.client.post(f"{self.api_base}/onbid/parse", json=parse_payload, headers=self.api_headers)
        assert parse_response.status_code == 200
        
        parse_data = parse_response.json()
        
        # 3. Verify no mock data was generated
        assert parse_data["status"] == "pending"
        assert parse_data["asset_type"] is None
        assert parse_data["use_type"] is None
        assert parse_data["address"] is None
        
        # 4. Verify appropriate error handling
        assert "error_code" in parse_data
        assert parse_data["error_code"] in ["ATTACHMENT_NONE", "REMOTE_HTTP_ERROR"]
        
        # 5. Check cache remains clean
        cache_response = self.client.get(f"{self.api_base}/debug/cache", headers=self.api_headers)
        cache_data = cache_response.json()
        
        # Cache should only contain STRICT mode entries (if any)
        if cache_data["cache_info"]["total_entries"] > 0:
            assert cache_data["cache_info"]["contaminated_entries"] == 0

# Golden Set Test Scenarios
class TestGoldenSetScenarios:
    """Test specific scenarios that must always work correctly in STRICT mode"""
    
    def setup_method(self):
        self.client = TestClient(app)
        self.api_headers = {"x-api-key": "dev"}
        self.api_base = "/api/v1"
    
    def test_known_case_numbers_behavior(self):
        """Test behavior with known case number patterns"""
        known_cases = [
            "2024-01774-006",  # Apartment case
            "2024-05180-001",  # Office case
            "2024-06499-010",  # Commercial case
        ]
        
        for case_no in known_cases:
            payload = {"case_no": case_no, "force": True}
            response = self.client.post(f"{self.api_base}/onbid/parse", json=payload, headers=self.api_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            # Should attempt real parsing, return empty if not found (no mock fallback)
            assert data["status"] in ["ok", "pending"]
            assert "case_no" in data
            assert "req_id" in data
            
            # In STRICT mode, if real data not found, should be empty
            if data["error_code"] == "ATTACHMENT_NONE":
                assert data["asset_type"] is None
                assert data["use_type"] is None
    
    def test_api_consistency_across_endpoints(self):
        """Test that all API endpoints maintain consistency in STRICT mode"""
        # Test health endpoint
        health_response = self.client.get(f"{self.api_base}/healthz")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "ok"
        
        # Test that core business logic endpoints still work
        profile_payload = {
            "job": "직장인",
            "annual_income": 78000000,
            "credit_score": 820,
            "existing_debt_principal": 0,
            "existing_debt_monthly_payment": 800000,
            "desired_ltv": 70,
            "cash_on_hand": 50000000
        }
        
        profile_response = self.client.post(f"{self.api_base}/profile", json=profile_payload, headers=self.api_headers)
        assert profile_response.status_code == 200
        assert "est_loan_limit" in profile_response.json()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])