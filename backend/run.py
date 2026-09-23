import os
from dotenv import load_dotenv

# Load from project root, overriding if necessary, or fallback
root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(root_env):
    load_dotenv(root_env)
else:
    load_dotenv()

from app import create_app

app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Flask Backend server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
