import os
from .base import *

DJANGO_ENV = os.environ.get("DJANGO_ENV", "prod")

if DJANGO_ENV == "prod":
    from .prod import *
else:
    from .dev import *