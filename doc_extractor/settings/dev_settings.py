from .settings import *

DEBUG = True

ALLOWED_HOSTS = ['172.28.42.150']

STATICFILES_DIRS = [
    # os.path.join(BASE_DIR, "/assets/"),
    r"/home/vijay/doc_extractor/assets/extractor/",
]

STATIC_ROOT = r"/home/vijay/doc_extractor/assets/"

# STATIC_URL = '/static/'
STATIC_URL = '/assets/'
# STATIC_URL = r"Schawk/doc_extractor/extractor/templates/"