from .settings import *

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1','localhost']

# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [os.path.join(BASE_DIR, 'BetaTemplates'),],
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.debug',
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#             ],
#         },
#     },
# ]

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "/assets/"),
    r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk/doc_extractor/assets/",
]

STATIC_URL = '/assets/'
