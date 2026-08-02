import os
from .base import *

import os
import sys

DJANGO_ENV = os.environ.get("DJANGO_ENV", "dev")

# Print for debugging
print(f"DJANGO_ENV: {DJANGO_ENV}", file=sys.stderr)
print(f"ALLOWED_HOSTS from env: {os.environ.get('ALLOWED_HOSTS', 'NOT SET')}", file=sys.stderr)

if DJANGO_ENV == "prod":
    from .prod import *
else:
    from .dev import *