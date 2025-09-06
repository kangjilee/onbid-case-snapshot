@echo off
echo Starting KOMA Auction Helper...
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Starting Streamlit app...
echo Open your browser to http://localhost:8501
echo Press Ctrl+C to stop the app
echo.
streamlit run app.py