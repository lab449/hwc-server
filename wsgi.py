import os
from hwc_server import app

ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", True)
app.run(host='0.0.0.0', port=5050)

