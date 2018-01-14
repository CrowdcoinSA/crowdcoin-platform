__author__ = 'droog'
from tastypie.authentication import BasicAuthentication
from django.contrib.auth.models import User
from tastypie.models import ApiKey

class SessionAuthentication (BasicAuthentication):
    def __init__(self, *args, **kwargs):
        super(SessionAuthentication , self).__init__(*args, **kwargs)
 
    def is_authenticated(self, request, **kwargs):
        from django.contrib.sessions.models import Session
        if 'sessionid' in request.COOKIES:
            s = Session.objects.get(pk=request.COOKIES['sessionid'])
            if '_auth_user_id' in s.get_decoded():
                u = User.objects.get(id=s.get_decoded()['_auth_user_id'])
                request.user = u
                return True
        return super(SessionAuthentication , self).is_authenticated(request, **kwargs)

class TokenAuthentication (BasicAuthentication):
    def __init__(self, *args, **kwargs):
        super(TokenAuthentication, self).__init__(*args, **kwargs)

    def is_authenticated(self, request, **kwargs):
        token = request.GET.get('token')
        if ApiKey.objects.filter(key=token).exists():
            request.user = ApiKey.objects.get(key=token).user
            return True
        else:
            return super(TokenAuthentication, self).is_authenticated(request, **kwargs)