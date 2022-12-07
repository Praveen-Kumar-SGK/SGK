from environment import MODE

print(MODE)
if MODE == 'local':
    from .local_settings import *
else:
    from .dev_settings import *