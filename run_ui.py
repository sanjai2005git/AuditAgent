import sys
from streamlit.web import cli as stcli

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "auditagent/ui/app.py", "--server.port=8501", "--server.headless=true"]
    sys.exit(stcli.main())
