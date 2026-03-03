
import sys
import os

os.chdir('/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')
sys.path.insert(0, '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32')
os.environ['ACTIVE_USER_ID'] = '1'

from src.intelligence.tools import get_active_user_id
print('user_id via env:', get_active_user_id())
