from django.contrib.auth.models import User
from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from tastypie.serializers import Serializer
from tastypie.authentication import (
    Authentication, ApiKeyAuthentication, BasicAuthentication,SessionAuthentication,
    MultiAuthentication)
from tastypie.authorization import Authorization, DjangoAuthorization
from tastypie.resources import ModelResource#,ALL_WITH_RELATIONS
from tastypie import fields
from website.api.exceptions import CustomBadRequest
from website.models import *
from website.utils import *
from website.api.authorization import *
from website.api.authentication import TokenAuthentication
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.exceptions import BadRequest
from datetime import datetime,timedelta
import logging
from django.db.models import Q
from website.utils import get_user_available_balance,register_new_user,thisisme_id_check
import json
from decimal import Decimal

logger = logging.getLogger(__name__)

class MultipartResource(object):
    def deserialize(self, request, data, format=None):
        if not format:
            format = request.META.get('CONTENT_TYPE', 'application/json')
        if format == 'application/x-www-form-urlencoded':
            return request.POST
        if format.startswith('multipart'):
            data = request.POST.copy()
            data.update(request.FILES)
            return data
        return super(MultipartResource, self).deserialize(request, data, format)


class CreateUserResource(ModelResource):
    user = fields.ForeignKey('website.api.resources.UserResource', 'user', full=True)

    class Meta:
        allowed_methods = ['post']
        always_return_data = True
        authentication = Authentication()
        authorization = Authorization()
        queryset = UserProfile.objects.all()
        resource_name = 'register'
        always_return_data = True
        serializer = Serializer(formats=['json'])

    def dehydrate(self, bundle):
        if "raw_password" in bundle.data['profile']:
            # Pop out raw_password and validate it
            # This will prevent re-validation because hydrate is called
            # multiple times
            # https://github.com/toastdriven/django-tastypie/issues/603
            # "Cannot resolve keyword 'raw_password' into field." won't occur

            raw_password = bundle.data['profile'].pop("raw_password")
            bundle.data.pop('profile')
            bundle.data["password"] = make_password(raw_password)
        return bundle


    def obj_create(self, bundle, **kwargs):
        REQUIRED_FIELDS = ["profile"]
        for field in REQUIRED_FIELDS:
            if field not in bundle.data:
                raise CustomBadRequest(
                    code="missing_key",
                    message="Must provide {missing_key} when creating a user profile."
                        .format(missing_key=field))
            else:
                REQUIRED_USER_PROFILE_FIELDS = ["username", "raw_password","pin","msisdn", "identification_no", "identification_country",
                                                "identification_type"]

                for field in REQUIRED_USER_PROFILE_FIELDS:
                    if field not in bundle.data['profile']:
                        raise CustomBadRequest(
                            code="missing_key",
                            message="Must provide {missing_key} when creating a user profile."
                                .format(missing_key=field))
                username = bundle.data["profile"]["username"]
                if User.objects.filter(username=username).exists():
                    raise CustomBadRequest(
                        code="already_exists",
                        message="Profile already exists")
                if  UniqueIdentifier.objects.filter(
                        name ='msisdn',
                        value=bundle.data["profile"]["msisdn"]):
                    raise CustomBadRequest(
                        code="already_exists",
                        message="Msisdn already exists.")

                registration_response = register_new_user(bundle.data["profile"])
                if registration_response['status'] is "error":
                    raise CustomBadRequest(code='registration_error', message=registration_response.get('message'))

                bundle.obj= UserProfile.objects.get(user__username=username)
                self._meta.resource_name = UserProfileResource._meta.resource_name
                return bundle


class UniqueIdentifierResource(ModelResource):
    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['post','get' ]
        queryset = UniqueIdentifier.objects.all()
        resource_name = 'identifiers'
        serializer = Serializer(formats=['json'])
        excludes = ['is_active']
     

class UserResource(ModelResource):
    # We need to store raw password in a virtual field because hydrate method
    # is called multiple times depending on if it's a POST/PUT/PATCH request
    raw_password = fields.CharField(attribute=None, readonly=True, null=True,
                                    blank=True)

    class Meta:
        # For authentication, allow both basic and api key so that the key
        # can be grabbed, if needed.
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        serializer = Serializer(formats=['json'])

        # Because this can be updated nested under the UserProfile, it needed
        # 'put'. No idea why, since patch is supposed to be able to handle
        # partial updates.
        allowed_methods = ['get', 'put' ]
        always_return_data = True
        queryset = User.objects.all().select_related("api_key")
        resource_name = "users"
        fields = ['last_name','first_name','username','is_active','email','password','is_staff','is_superuser']
        filtering = {'username':ALL_WITH_RELATIONS,'email':ALL}

    def authorized_read_list(self, object_list, bundle):
        return object_list.filter(id=bundle.request.user.id).select_related()

    def authorized_read_detail(self, object_list, bundle):
        user_profile = object_list.get(id=bundle.request.user.id)
        return user_profile

    def dehydrate(self, bundle):
        bundle.data['key'] = bundle.obj.api_key.key
 
        return bundle

 
class UserProfileResource(ModelResource):
    user = fields.ForeignKey(UserResource, 'user', full=True)
    identifier = fields.ManyToManyField(UniqueIdentifierResource,'identifier',full=True, null=True,blank=True)
    default_pocket = fields.ForeignKey('website.api.resources.PocketResource', 'default_pocket', full=True)
    pockets = fields.ManyToManyField('website.api.resources.PocketResource', 'pockets',full=True, null=True, blank=True)
    class Meta:
        # For authentication, allow both basic and api key so that the key
        # can be grabbed, if needed.
        authentication = MultiAuthentication(
            ApiKeyAuthentication(),
            BasicAuthentication(),
            TokenAuthentication())
        authorization = UserAuthorization()
        always_return_data = True
        allowed_methods = ['get', 'patch','put' ]
        detail_allowed_methods = ['get', 'put']
        queryset = UserProfile.objects.all()
        resource_name = 'profile'
        filtering = {'user':ALL_WITH_RELATIONS, 'identifier':ALL_WITH_RELATIONS}
        serializer = Serializer(formats=['json'])
 
    def authorized_read_list(self, object_list, bundle):
        return object_list.filter(user__username=bundle.request.user.username).select_related()
 
    ## Since there is only one user profile object, call get_detail instead
    def get_list(self, request, **kwargs):
        kwargs["user"] = request.user
        return super(UserProfileResource, self).get_detail(request, **kwargs)




class NetworkResource(ModelResource):
    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get' ]
        queryset = Network.objects.all()
        resource_name = 'networks'
        serializer = Serializer(formats=['json'])
        excludes = ["daily_limit","airtime_transfer_limit","is_active","created"]

    def hydrate(self, bundle):
        REQUIRED_FIELDS = ["name"]
        for field in REQUIRED_FIELDS:
            if field not in bundle.data:
                raise CustomBadRequest(
                    code="missing_key",
                    message="Must provide {missing_key} when creating a Network."
                        .format(missing_key=field))

class SimCardResource(ModelResource):
    network = fields.ForeignKey(
        'website.api.resources.NetworkResource',
        'network',
        full=True,
        help_text="Network Carrier"
    )
    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get' ]
        queryset = SimCard.objects.all()
        resource_name = 'sim_cards'
        serializer = Serializer(formats=['json'])
        excludes = ["balance_month","balance_day","sim_no","status","is_active","created"]

    def dehydrate(self, bundle):
        bundle.data['instructions'] = bundle.obj.network.airtime_transfer_instructions.format(
            amount=int(bundle.obj.balance_day), msisdn=bundle.obj.msisdn)
        return bundle

    def hydrate(self, bundle):
        REQUIRED_FIELDS = ["network","msisdn","sim_no","balance_day"]
        for field in REQUIRED_FIELDS:
            if field not in bundle.data:
                raise CustomBadRequest(
                    code="missing_key",
                    message="Must provide {missing_key} when creating a Sim card."
                        .format(missing_key=field))

class TransactionResource(ModelResource):
    identifiers = fields.ManyToManyField('website.api.resources.UniqueIdentifierResource', 'identifiers', full=True)
    pocket = fields.ForeignKey('website.api.resources.PocketResource', 'pocket', full=True,null=True)

    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(), TokenAuthentication())
        authorization = PocketAuthorization()
        always_return_data = True
        allowed_methods = ['get']
        queryset = Transaction.objects.all()
        resource_name = 'transactions'
        serializer = Serializer(formats=['json'])
        exclude = []
        filtering = {'pocket':ALL_WITH_RELATIONS}
        ordering = ['datetime']

    def dehydrate(self, bundle):
        bundle.data['description'] = []
        for tag in bundle.obj.identifiers.all():
            bundle.data['description'].append(tag.value)
        return bundle

    def hydrate(self, bundle):
        REQUIRED_FIELDS = ["pocket","amount","debit"]
        for field in REQUIRED_FIELDS:
            if field not in bundle.data:
                raise CustomBadRequest(
                    code="missing_key",
                    message="Must provide {missing_key} when creating a Transaction."
                        .format(missing_key=field))

class PocketResource(ModelResource):
    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(), TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get', 'post']
        queryset = Pocket.objects.all()
        resource_name = 'pockets'
        serializer = Serializer(formats=['json'])
        filtering = {'identifiers': ALL_WITH_RELATIONS, 'transactions': ALL_WITH_RELATIONS, 'name':ALL, 'tag':ALL}
        exclude = []

    def dehydrate(self, bundle):
        bundle.data['balance'] = Decimal(bundle.obj.balance())
        return bundle

    def hydrate(self, bundle):
        REQUIRED_FIELDS = ["name","tag"]
        for field in REQUIRED_FIELDS:
            if field not in bundle.data:
                raise CustomBadRequest(
                    code="missing_key",
                    message="Must provide {missing_key} when creating a Pocket."
                        .format(missing_key=field))


class AirtimeDepositLeadResource(MultipartResource,ModelResource):
    pocket = fields.ForeignKey('website.api.resources.PocketResource', 'pocket', full=True, null=True)
    sim_card = fields.ForeignKey('website.api.resources.SimCardResource', 'sim_card', full=True, null=True,blank=True)
    #identifiers = fields.ManyToManyField('website.api.resources.UniqueIdentifierResource', 'identifiers', full=True,
    #                                     null=True)
    #transactions = fields.ManyToManyField('website.api.resources.TransactionResource', 'transactions', full=True,null=True)
    network = fields.CharField()

    class Meta:
        authentication = MultiAuthentication(
            ApiKeyAuthentication(),
            BasicAuthentication(),
            TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get','post' ]
        queryset = AirtimeDepositLead.objects.all()
        resource_name = 'airtime_deposits'
        serializer = Serializer()
        excludes = ['transactions','identifiers']


    def hydrate(self, bundle, **kwargs):
        REQUIRED_FIELDS = [ "amount", "network"]
        for field in REQUIRED_FIELDS:
            if field not in bundle.data:
                raise CustomBadRequest(
                    code="missing_key",
                    message="Must provide {missing_key} when creating a Airtime deposit."
                        .format(missing_key=field))
        sim_request = prepare_sim_deposit(amount=bundle.data.get('amount'), network=bundle.data.get('network'))
        logger.info(sim_request)

        if sim_request['status'] == "success":
            sim = sim_request['message']
            bundle.data['sim_card'] = sim
        else:
            raise CustomBadRequest(
                code=sim_request['code'],
                message=sim_request['message'])                

        return bundle



class BankDepositLeadResource(ModelResource):
    pocket = fields.ForeignKey('website.api.resources.PocketResource', 'pocket', full=True)
    identifiers = fields.ManyToManyField('website.api.resources.UniqueIdentifierResource', 'identifiers', full=True,
                                         null=True)

    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get','post' ]
        queryset = BankDepositLead.objects.all()
        resource_name = 'bank_deposits'
        serializer = Serializer(formats=['json'])
        exclude = []

    def hydrate(self, bundle):
        REQUIRED_FIELDS = ["pocket","reference","amount"]
        for field in REQUIRED_FIELDS:
            if field not in bundle.data:
                raise CustomBadRequest(
                    code="missing_key",
                    message="Must provide {missing_key} when creating a Bank deposit."
                        .format(missing_key=field))


class BankPaymentLeadResource(ModelResource):
    pocket = fields.ForeignKey('website.api.resources.PocketResource', 'pocket', full=True)
    identifiers = fields.ManyToManyField('website.api.resources.UniqueIdentifierResource', 'identifiers', full=True,
                                         null=True)
    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get','post']
        queryset = BankPaymentLead.objects.all()
        resource_name = 'bank_payments'
        serializer = Serializer(formats=['json'])

    def hydrate(self, bundle):
        if bundle.request.method == "POST":
            REQUIRED_FIELDS = ["pocket","bank","amount","account_no"]
            for field in REQUIRED_FIELDS:
                if field not in bundle.data:
                    raise CustomBadRequest(
                        code="missing_key",
                        message="Must provide {missing_key} when creating a Bank payment."
                            .format(missing_key=field))
            if Pocket.objects.filter(tag=bundle.data.get("pocket"),active=True).exists():
                pocket = Pocket.objects.get(tag=bundle.data.get("pocket"),active=True)
                user_profile = UserProfile.objects.get(user=bundle.request.user)
                if not pocket in user_profile.pockets.all():
                    raise CustomBadRequest(
                        code="unauthorised",
                        message="You do not own {missing_key}."
                            .format(missing_key=bundle.data.get("pocket")))

                if not pocket.balance() >= bundle.data.get("amount"):
                    raise CustomBadRequest(
                        code="insufficient_balance",
                        message="You do not have enough balance in {missing_key}."
                            .format(missing_key=bundle.data.get("pocket_from")))
                bundle.data["pocket"] = pocket
                return bundle

            else:
                raise CustomBadRequest(
                    code="invalid_key",
                    message="Could not find any Pocket matching {missing_key}.".format(missing_key=bundle.data.get('pocket')))
        return bundle

class CrowdcoinPaymentLeadResource(MultipartResource,ModelResource):
    pocket_from = fields.ForeignKey('website.api.resources.PocketResource', 'pocket_from', full=True, null=True)
    pocket_to = fields.ForeignKey('website.api.resources.PocketResource', 'pocket_to', full=True)
    identifiers = fields.ManyToManyField('website.api.resources.UniqueIdentifierResource', 'identifiers', full=True,null=True)
    airtime_deposit_lead = fields.ForeignKey('website.api.resources.AirtimeDepositLeadResource', 'airtime_deposit_lead', full=True, null=True)
    class Meta:
        authentication = MultiAuthentication(
            ApiKeyAuthentication(),
            BasicAuthentication(),
            TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get','post' ]
        queryset = CrowdcoinPaymentLead.objects.all()
        resource_name = 'crowdcoin_payments'
        serializer = Serializer(formats=['json'])
        filtering = {'status': ALL,'pocket_to': ALL_WITH_RELATIONS,'reference': ALL}
        exclude = []

    def hydrate(self, bundle):
        REQUIRED_FIELDS = ["pocket_to","amount","reference"]
        for field in REQUIRED_FIELDS:
            if field not in bundle.data:
                raise CustomBadRequest(
                    code="missing_key",
                    message="Must provide {missing_key} when creating a Crowdcoin payment."
                        .format(missing_key=field)
                        )
        try:
            pocket_from = PocketResource().get_via_uri(bundle.data.get("pocket_from"))
        except Exception as e:
            pocket_from = None
        pocket_to = PocketResource().get_via_uri(bundle.data.get("pocket_to"))

        user_profile = UserProfile.objects.get(user=bundle.request.user)
        if pocket_from :
            if not pocket_from in user_profile.pockets.all():
                raise CustomBadRequest(
                    code="unauthorised",
                    message="You do not own {missing_key}."
                        .format(missing_key=bundle.data.get("pocket")))

            if not pocket_from.balance() >= float(bundle.data.get("amount")):
                raise CustomBadRequest(
                    code="insufficient_balance",
                    message="You do not have enough balance in {missing_key}."
                        .format(missing_key=bundle.data.get("pocket_from")))
        logger.info(bundle.data)

        # if bundle.data.get('identifiers'):
        #     identifiers = []
        #     for identifier in bundle.data.get('identifiers'): 
        #         logger.info(identifier)
        #         identifiers.append( UniqueIdentifier.objects.get_or_create(name=identifier['name'],value=identifier['value'])[0].pk)
        #     bundle.data['identifiers'] = identifiers
        return bundle


class SmsInboundResource(MultipartResource,ModelResource):
    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get' ]
        queryset = SmsInbound.objects.all()
        resource_name = 'sms_inbox'
        serializer = Serializer()
        exclude = []


class SmsOutBoundResource(MultipartResource,ModelResource):
    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get','post' ]
        queryset = SmsOutBound.objects.all()
        resource_name = 'sms_outbound'
        serializer = Serializer(formats=['json'])
        exclude = []

    def hydrate(self, bundle):
        REQUIRED_FIELDS = ["message","msisdn"]
        for field in REQUIRED_FIELDS:
            if field not in bundle.data:
                raise CustomBadRequest(
                    code="missing_key",
                    message="Must provide {missing_key} when creating an Outboud SMS."
                        .format(missing_key=field)
                        )        
        return bundle

class MerchantResource(ModelResource):
    default_pocket = fields.ForeignKey('website.api.resources.PocketResource', 'default_pocket', full=True,null=True)
    profile = fields.ForeignKey('website.api.resources.UserProfileResource', 'profile', full=True,null=True)
    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get']
        detail_allowed_methods = ['get', 'put']
        queryset = Merchant.objects.all()
        resource_name = 'merchants'
        serializer = Serializer()
        exclude = []
        filtering = {'default_pocket':ALL_WITH_RELATIONS,'profile':ALL_WITH_RELATIONS,'display_on_website':ALL}


class PromotionResource(ModelResource):
    referrer = fields.ForeignKey('website.api.resources.PocketResource', 'referrer', full=True,null=True)

    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get' ]
        queryset = Promotion.objects.all()
        resource_name = 'promotions'
        serializer = Serializer()
        filtering = {'referrer':ALL_WITH_RELATIONS}
        exclude = []


class ClaimedPromotionResource(ModelResource):
    referred = fields.ForeignKey('website.api.resources.PocketResource', 'referred', full=True,null=True)

    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get' ,'post']
        queryset = ClaimedPromotion.objects.all()
        resource_name = 'claimed_promotions'
        serializer = Serializer()
        exclude = []



class VoucherPaymentLeadResource(MultipartResource,ModelResource):
    pocket_to = fields.ForeignKey('website.api.resources.PocketResource', 'pocket_to', full=True, null=True)
    pocket_from = fields.ForeignKey('website.api.resources.PocketResource', 'pocket_from', full=True, null=True)

    class Meta:
        authentication = MultiAuthentication(
            BasicAuthentication(),
            ApiKeyAuthentication(),TokenAuthentication())
        authorization = Authorization()
        always_return_data = True
        allowed_methods = ['get','post','put' ]
        queryset = VoucherPaymentLead.objects.all()
        resource_name = 'voucher_payments'
        serializer = Serializer()
        filtering = {'voucher_code':ALL_WITH_RELATIONS,'pocket_from':ALL_WITH_RELATIONS,'security_pin':ALL_WITH_RELATIONS}
        ordering = ['created']
        exclude = []

    def hydrate(self, bundle):
        if bundle.request.method == 'POST':
            REQUIRED_FIELDS = ["pocket_from","amount","recipient_msisdn"]
            for field in REQUIRED_FIELDS:
                if field not in bundle.data:
                    raise CustomBadRequest(
                        code="missing_key",
                        message="Must provide {missing_key} when creating a Crowdcoin payment."
                            .format(missing_key=field))
            if bundle.data.get("pocket_from") == "default":
                pocket_from_uri = PocketResource().get_resource_uri(UserProfile.objects.get(user=bundle.request.user).default_pocket)
            else:
                pocket_from_uri = bundle.data.get("pocket_from")
            pocket_from = PocketResource().get_via_uri(pocket_from_uri)
            if pocket_from.active:
                transaction_pocket_from = pocket_from
                user_profile = UserProfile.objects.get(user=bundle.request.user)
                if not transaction_pocket_from in user_profile.pockets.all():
                    raise CustomBadRequest(
                        code="unauthorised",
                        message="You do not own {missing_key}."
                            .format(missing_key=bundle.data.get("pocket")))

                if not transaction_pocket_from.balance() >= float(bundle.data.get("amount")):
                    raise CustomBadRequest(
                        code="insufficient_balance",
                        message="You do not have enough funds available in {missing_key}."
                            .format(missing_key=pocket_from.name))

            else:
                raise CustomBadRequest(
                    code="invalid_key",
                    message="Could not find any Pocket matching {missing_key}."
                        .format(missing_key=bundle.data.get("pocket_from")))
            bundle.data["pocket_from"] = transaction_pocket_from

        elif bundle.request.method == 'PUT':
            bundle.data["status"] = 'Collected'
        return bundle
