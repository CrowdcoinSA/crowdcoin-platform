from django.conf.urls import  include, url
from django.contrib.auth import views as auth_views
from django.contrib import admin
from website.views import *
from django.conf.urls.static import static
from django.views import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from tastypie.api import Api
from website.api.resources import *

admin.autodiscover()
admin.site.site_header = 'Crowdcoin Dashboard'
#handler404='website.views.custom_404'
#handler500='website.views.custom_500'
api_prefix = "api/v1/"
v1_api = Api(api_name='v1')
v1_api.register(UserProfileResource())
v1_api.register(CreateUserResource())
v1_api.register(UserResource())
v1_api.register(SimCardResource())
v1_api.register(NetworkResource())
v1_api.register(UniqueIdentifierResource())
v1_api.register(AirtimeDepositLeadResource())
v1_api.register(PocketResource())
v1_api.register(TransactionResource())
v1_api.register(CrowdcoinPaymentLeadResource())
v1_api.register(BankPaymentLeadResource())
v1_api.register(BankDepositLeadResource())
v1_api.register(SmsInboundResource())
v1_api.register(VoucherPaymentLeadResource())
v1_api.register(MerchantResource())
v1_api.register(PromotionResource())
v1_api.register(ClaimedPromotionResource())
v1_api.register(SmsOutBoundResource())

urlpatterns = [
                url(r'^admin/', admin.site.urls),
                url(r'^api/', include(v1_api.urls)),
                url(r'^static/(?P<path>.*)$', static.serve, {'document_root': settings.STATIC_ROOT}),
                url(r'^%ssupport_ticket_create/$' % api_prefix, view=support_ticket_create),
                url(r'^%ssmsinbound$' % api_prefix, view=SmsInboundView, name='smsinbound'),
                url(r'^%screate_transaction/$' % api_prefix, view=create_funds_transaction_api),
                url(r'^%sreset_password/$' % api_prefix, view=reset_password),
                url(r'^%sdeposit_lead/$' % api_prefix, view=api_generate_deposit_lead),
                url(r'^%sexport/$' % api_prefix, view=export_funds_csv),
                url(r'^%slogin/$' % api_prefix, view=api_login),
                url(r'^%sregister_merchant/$' % api_prefix, view=api_merchant_registration),
                url(r'^%sussd/$' % api_prefix, view=ussdView, name='ussd'),
                url(r'^%sotp/$' % api_prefix, get_otp_view, name='get_otp'),
                url(r'^loaderio-b193a2f576f0426fef58ef4dbe597971/$', view=loaderio),
                #url(r'^sso/', include('freshdesk.urls')),
                url(r'^$', view=LandingView, name="landing")
]+ staticfiles_urlpatterns()

