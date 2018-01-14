import os
import sys
import site

# Add the site-packages of the chosen virtualenv to work with
#site.addsitedir('/var/www/crowdcoin.co.za/env/lib/python2.7/site-packages')

# Add the app's directory to the PYTHONPATH
#sys.path.append('/var/www/crowdcoin.co.za/crowdcoin/')

os.environ['DJANGO_SETTINGS_MODULE'] = 'crowdcoincoza.settings'

# Activate your virtual env
#activate_env=os.path.expanduser("/var/www/crowdcoin.co.za/env/bin/activate_this.py")
#execfile(activate_env, dict(__file__=activate_env))

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
