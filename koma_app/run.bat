@echo off
echo ====================================
echo KOMA 공매 도우미 시작
echo ====================================
echo.
echo 의존성 설치 중...
pip install -r requirements.txt
echo.
echo Streamlit 앱 시작 중...
echo 브라우저에서 http://localhost:8501 를 열어주세요
echo 앱을 중지하려면 Ctrl+C를 누르세요
echo.
streamlit run app.py