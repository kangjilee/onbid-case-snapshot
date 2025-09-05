import pytest
import json
from pathlib import Path
from onbid_parser import OnbidParser
from models import OnbidParseResponse


class TestOnbidParser:
    """Unit tests for OnbidParser with mock HTML content validation"""
    
    def setup_method(self):
        self.parser = OnbidParser()
    
    def test_flag_detection_지분(self):
        """Test 지분 flag detection with regex patterns"""
        content_with_flag = "압류재산 매각 공고\n공유지분 1/3 매각\n감정가: 5억원"
        content_without_flag = "압류재산 매각 공고\n단독 소유권 매각\n감정가: 5억원"
        
        flags_with = self.parser.detect_flags(content_with_flag)
        flags_without = self.parser.detect_flags(content_without_flag)
        
        assert flags_with.지분 == True
        assert flags_without.지분 == False
    
    def test_flag_detection_대지권없음(self):
        """Test 대지권없음 flag detection"""
        content_with_flag = "국유재산 매각 공고\n대지권 미등기 상태\n오피스텔"
        content_without_flag = "국유재산 매각 공고\n대지권 등기 완료\n오피스텔"
        
        flags_with = self.parser.detect_flags(content_with_flag)
        flags_without = self.parser.detect_flags(content_without_flag)
        
        assert flags_with.대지권없음 == True
        assert flags_without.대지권없음 == False
    
    def test_flag_detection_건물만(self):
        """Test 건물만 flag detection"""
        content_with_flag = "압류재산 매각 공고\n건물만 매각 (토지 제외)\n근린상가"
        content_without_flag = "압류재산 매각 공고\n토지 및 건물 일괄 매각\n근린상가"
        
        flags_with = self.parser.detect_flags(content_with_flag)
        flags_without = self.parser.detect_flags(content_without_flag)
        
        assert flags_with.건물만 == True
        assert flags_without.건물만 == False
    
    def test_flag_detection_부가세(self):
        """Test 부가세 flag detection"""
        content_with_flag = "압류재산 매각 공고\n부가가치세 별도 과세\n근린상가"
        content_without_flag = "압류재산 매각 공고\n면세 대상\n주거용 건물"
        
        flags_with = self.parser.detect_flags(content_with_flag)
        flags_without = self.parser.detect_flags(content_without_flag)
        
        assert flags_with.부가세 == True
        assert flags_without.부가세 == False
    
    def test_flag_detection_특약(self):
        """Test 특약 flag detection"""
        content_with_flag = "압류재산 매각 공고\n특약사항: 매수인은 임차인 권리 승계\n근린상가"
        content_without_flag = "압류재산 매각 공고\n별도 조건 없음\n근린상가"
        
        flags_with = self.parser.detect_flags(content_with_flag)
        flags_without = self.parser.detect_flags(content_without_flag)
        
        assert flags_with.특약 == True
        assert flags_without.특약 == False
    
    def test_parse_monetary_value(self):
        """Test Korean monetary value parsing"""
        test_cases = [
            ("2억 3500만원", 235000000.0),
            ("15억 원", 1500000000.0),
            ("850만원", 8500000.0),
            ("5000원", 5000.0),
            ("3.5억원", 350000000.0),
            ("", None),
            ("invalid", None)
        ]
        
        for text, expected in test_cases:
            result = self.parser.parse_monetary_value(text)
            assert result == expected, f"Failed for input: {text}"
    
    def test_extract_case_no_from_url(self):
        """Test case number extraction from various URL patterns"""
        test_cases = [
            ("https://www.onbid.co.kr/auction/case/12345", "12345"),
            ("https://onbid.co.kr/case/ABC-123", "ABC-123"),
            ("https://www.onbid.co.kr/auction?caseNo=TEST-789", "TEST-789"),
            ("https://onbid.co.kr/auction/view/555888", "555888"),
            ("https://invalid-url-no-pattern.com", None)  # Will generate hash-based ID
        ]
        
        for url, expected in test_cases:
            result = self.parser.extract_case_no(url)
            if expected:
                assert result == expected
            else:
                assert result.startswith("URL_")
    
    def test_parse_onbid_case_with_url(self):
        """Test complete parsing flow with URL input"""
        test_url = "https://www.onbid.co.kr/auction/case/TEST123"
        
        result = self.parser.parse_onbid_case(url=test_url)
        
        # Validate response structure
        assert isinstance(result, OnbidParseResponse)
        assert result.status == "ok"
        assert result.case_no == "TEST123"
        assert result.req_id is not None
        
        # Validate required fields (8+ non-null keys)
        non_null_fields = [
            result.asset_type,
            result.use_type,
            result.address,
            result.areas,
            result.pay_due,
            result.flags,
            result.status,
            result.case_no
        ]
        
        assert all(field is not None for field in non_null_fields)
        assert len([f for f in non_null_fields if f is not None]) >= 8
    
    def test_parse_onbid_case_with_case_no(self):
        """Test complete parsing flow with case_no input"""
        test_case_no = "DIRECT456"
        
        result = self.parser.parse_onbid_case(case_no=test_case_no)
        
        # Validate response structure
        assert isinstance(result, OnbidParseResponse)
        assert result.status == "ok"
        assert result.case_no == "DIRECT456"
        assert result.req_id is not None
    
    def test_file_storage_creation(self):
        """Test file storage and data persistence"""
        test_case_no = "STORAGE789"
        
        result = self.parser.parse_onbid_case(case_no=test_case_no)
        
        # Check file creation
        expected_dir = Path("data/raw") / test_case_no
        expected_file = expected_dir / "raw_data.json"
        
        assert expected_dir.exists()
        assert expected_file.exists()
        
        # Validate JSON content
        with open(expected_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        
        assert saved_data["case_no"] == test_case_no
        assert "parsed_at" in saved_data
        assert "parsed_data" in saved_data
    
    def test_validation_errors(self):
        """Test input validation"""
        # Should raise error when neither case_no nor url provided
        with pytest.raises(ValueError, match="Either case_no or url must be provided"):
            self.parser.parse_onbid_case()
        
        # Should raise error when URL cannot be parsed to case_no
        with pytest.raises(ValueError, match="Could not extract or determine case number"):
            self.parser.parse_onbid_case(url="invalid-url-that-returns-none")
    
    def test_mock_content_generation_variety(self):
        """Test that different case numbers generate different content types"""
        case_numbers = ["TEST001", "TEST002", "TEST003"]
        contents = []
        
        for case_no in case_numbers:
            content = self.parser._generate_mock_content(case_no, None)
            contents.append(content)
        
        # Should have different asset types across the mock templates
        asset_types = []
        for content in contents:
            if "압류재산" in content:
                asset_types.append("압류재산")
            elif "국유재산" in content:
                asset_types.append("국유재산")
            elif "수탁재산" in content:
                asset_types.append("수탁재산")
        
        # At least 2 different asset types should be generated
        assert len(set(asset_types)) >= 2