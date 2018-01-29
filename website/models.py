from django.db import models
from django.contrib.auth.models import User,Group
from django.db.models import Sum
import decimal
import logging

logger = logging.getLogger(__name__)

class UserProfile(models.Model):
    user = models.OneToOneField(User,blank=True,null=True)
    pin = models.CharField(max_length=10,default='0000',null=True, blank=True)
    identifier = models.ManyToManyField('UniqueIdentifier', blank=True, related_name="user_profile_identifier")
    is_verified = models.BooleanField(default=False)
    identification_no = models.CharField(max_length=50,blank=True,null=True)
    identification_country = models.CharField(max_length=50,blank=True,null=True)
    identification_type = models.CharField(max_length=50,blank=True,null=True)
    street_address = models.TextField(max_length=50, blank=True, null=True)
    suburb = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    province = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    vital_status =  models.CharField(max_length=50,blank=True,null=True)
    gender = models.CharField(max_length=50, blank=True, null=True)
    d_o_b = models.DateField( blank=True, null=True)
    network = models.CharField(max_length=50,blank=True,null=True)
    msisdn = models.CharField(max_length=50, blank=True, null=True)
    referrer = models.CharField(max_length=100, blank=True, null=True)
    display_name = models.CharField(max_length=100, blank=True, null=True)
    pockets = models.ManyToManyField('Pocket', related_name="user_profile_pocket",blank=True)
    default_pocket = models.ForeignKey('Pocket',related_name="user_profile_default_pocket",null=True,blank=True)

    def __unicode__(self):
        return "%s : %s"% (self.user.username, self.default_pocket)

class Merchant(models.Model):
    profile = models.ForeignKey('UserProfile',related_name='merchant_profile')
    trading_name = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    registration_number = models.CharField(max_length=50, blank=True, null=True)
    telephone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField( blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    street_address = models.TextField(max_length=50, blank=True, null=True)
    suburb = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    province = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_number = models.CharField(max_length=100, blank=True, null=True)
    bank_branch_code = models.CharField(max_length=100, blank=True, null=True)
    payout_frequency = models.IntegerField(default=1,blank=True,null=True)
    callback_url = models.URLField(blank=True,null=True,default='http://')
    callback_method = models.CharField(max_length=100,default='POST')
    email_notification = models.EmailField(blank=True,null=True)
    subscription= models.CharField(max_length=100,default="Trial",choices=(("Trial","Trial"),
                                                                   ("Premium","Premium"),
                                                                   ("Enterprise","Enterprise")))    
    default_pocket = models.ForeignKey('Pocket',related_name="merchant_profile_default_pocket",null=True,blank=True)    
    active = models.BooleanField(default=True)
    display_on_website = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s : %s"% (self.profile.user.username, self.trading_name)


class Promotion(models.Model):
    referrer = models.ForeignKey('Pocket',related_name="referrer_pocket",null=True,blank=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    discount_amount = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    reward_amount = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    datetime = models.DateTimeField(auto_created=True,null=True,blank=True)
    available = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return "%s %s" % (self.code, self.description)


class ClaimedPromotion(models.Model):
    
    """docstring for ClaimedPromotion"""
    promotion = models.ForeignKey('Promotion',related_name="promotion")
    referred = models.ForeignKey('Pocket',related_name="referred_pocket",null=True,blank=True)
    datetime = models.DateTimeField(auto_created=True,null=True,blank=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return "%s %s" % (self.promotion.code, self.referrer.tag)
        


class Transaction(models.Model):
    debit = models.BooleanField(default=True)
    pocket = models.ForeignKey('Pocket',blank=True, null=True, related_name="transaction_pocket")
    identifiers = models.ManyToManyField('UniqueIdentifier',  blank=True, related_name="transaction_identifiers")
    amount = models.DecimalField(decimal_places=2, max_digits=20)
    datetime = models.DateTimeField(auto_created=True,null=True,blank=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return "%s %s" % (self.amount, self.datetime)


class Pocket(models.Model):
    name = models.CharField(max_length=120)
    tag = models.CharField(max_length=120,null=True,blank=True)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    voucher_sending_fee = models.CharField(max_length=100,default='0%',blank=True)
    voucher_receiving_fee = models.CharField(max_length=100,default='0%',blank=True)
    payout_hold_days = models.IntegerField(default=7)
    payout_monthly_limit = models.DecimalField(decimal_places=2, max_digits=20, default=10000)

    def __unicode__(self):
        return "%s" % self.name

    def balance(self):
        transactions = Transaction.objects.filter(pocket=self)
        credits = transactions.filter(debit=False,active=True).aggregate(Sum('amount'))['amount__sum']
        debits = transactions.filter(debit=True,active=True).aggregate(Sum('amount'))['amount__sum']

        if credits is None:
            credits = 0
        if debits is None:
            debits = 0

        return credits-debits



class SmsInbound(models.Model):
    msisdn = models.CharField(max_length=150,blank=True,null=True)
    sender = models.CharField(max_length=150,blank=True,null=True)
    message = models.CharField(max_length=500,blank=True,null=True)
    msg_id = models.CharField(max_length=150,blank=True,null=True)
    source_id = models.CharField(max_length=150,blank=True,null=True)
    network_id = models.CharField(max_length=150,blank=True,null=True)
    received_time = models.DateTimeField(blank=True,auto_now=True,null=True)
    is_read = models.BooleanField(default=False,blank=True)
    replied = models.BooleanField(default=False,blank=True)

    def __unicode__(self):
        return self.message

class SmsOutBound(models.Model):
    recipient = models.ForeignKey(UserProfile,null=True,blank=True)
    msisdn = models.CharField(max_length=500,null=True,blank=True)
    message = models.CharField(max_length=500)
    datetime = models.DateTimeField(auto_now=True)
    status_string = models.CharField(max_length=50,blank=True,null=True)
    status_code = models.IntegerField(blank=True,null=True)
    source_id = models.CharField(max_length=100,blank=True,null=True)
    is_dispatched = models.BooleanField(default=False,blank=True)

    def __unicode__(self):
        return self.message


class Network(models.Model):
    name = models.CharField(max_length=20,blank=True,null=True)
    created = models.DateTimeField(auto_now_add=True)
    support_number = models.CharField(max_length=20,blank=True,null=True)
    is_active = models.BooleanField(default=False)
    airtime_transfer_limit = models.IntegerField(default=1000)
    daily_limit = models.FloatField(default=200,null=True,blank=True)
    airtime_transfer_instructions = models.TextField(max_length=500,blank=True,null=True)
    deposit_denominations = models.CharField(max_length=200,blank=True,null=True,default="5,10")
    deposit_fee = models.FloatField(default=10,null=True,blank=True)
    def __unicode__(self):
        return str(self.name)


class SimCard(models.Model):
    network = models.ForeignKey(Network,blank=True,null=True)
    created = models.DateTimeField(auto_now_add=True)
    balance_day = models.FloatField(blank=True,null=True,default=0)
    balance_month = models.FloatField(blank=True,null=True,default=0)
    msisdn = models.CharField(max_length=20,blank=True,null=True)
    online_password = models.CharField(max_length=100,blank=True,null=True)
    sim_no = models.CharField(max_length=50,unique=True)
    is_active = models.BooleanField(default=False)
    status= models.CharField(max_length=100,default="New",choices=(("New","New"),
                                                                   ("Deactivated","Deactivated"),
                                                                   ("Receiving","Receiving"),
                                                                   ("Paused","Paused"),
                                                                   ("Dispatch","Dispatch"),
                                                                   ("Circulating","Circulating")))

    def __unicode__(self):
        return "%s:  %s  bal:R %s" % (self.network,self.msisdn,self.balance_day)


class UniqueIdentifier(models.Model):
    name = models.CharField(max_length=150,blank=True,null=True)
    value = models.CharField(max_length=150,blank=True,null=True)
    is_active = models.BooleanField(default=True)

    def __unicode__(self):
        return "%s : %s" % (self.name, self.value)


class AirtimeDepositTransaction(models.Model):
    sim_card = models.ForeignKey(SimCard,blank=True, null=True, related_name="airtime_deposit_transaction_sim_card")
    amount = models.DecimalField(max_digits=20,decimal_places=2, default=0)
    reference = models.CharField(max_length=100,unique=True)
    description = models.CharField(max_length=200,null=True,blank=True)
    expiary_date = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(null=True,blank=True)
    active = models.BooleanField(default=False, blank=True)

    def __unicode__(self):
        return self.reference        


class AirtimeDepositLead(models.Model):
    pocket = models.ForeignKey(Pocket,related_name='airtime_deposit_lead_pocket',blank=True,null=True)
    sim_card = models.ForeignKey(SimCard,null=True,blank=True, related_name="airtime_deposit_lead_sim_card")
    amount = models.DecimalField(max_digits=20,decimal_places=2,default=0)
    identifiers = models.ManyToManyField(UniqueIdentifier, related_name="airtime_deposit_identifiers", blank=True)
    transactions = models.ManyToManyField(Transaction, related_name="airtime_deposit_lead_transactions", blank=True)
    airtime_deposit_transactions = models.ManyToManyField(AirtimeDepositTransaction, related_name="airtime_deposit_transactions", blank=True)
    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100, default="Pending", choices=(("Pending", "Pending"),
                                                                          ("Accepted", "Accepted"),
                                                                          ("Declined", "Declined"),
                                                                          ("Canceled", "Canceled")))
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return "%s : %s" % (self.status, self.amount)


class BankDepositLead(models.Model):
    pocket = models.ForeignKey(Pocket,related_name='bank_deposit_lead_pocket')
    amount = models.DecimalField(max_digits=20,decimal_places=2)
    reference = models.CharField(max_length=150, blank=True, null=True)
    identifiers = models.ManyToManyField(UniqueIdentifier, blank=True)
    transactions = models.ManyToManyField(Transaction, related_name="bank_deposit_lead_transactions", blank=True)
    status = models.CharField(max_length=100, default="Pending", choices=(("Pending", "Pending"),
                                                                          ("Accepted", "Accepted"),
                                                                          ("Declined", "Declined"),
                                                                          ("Canceled", "Canceled")))
    created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return "%s %s: %s" % (self.pocket, self.reference, self.amount)

class CrowdcoinPaymentLead(models.Model):
    pocket_from = models.ForeignKey(Pocket, related_name='crowdcoin_payment_lead_pocket_from', null=True,blank=True)
    pocket_to = models.ForeignKey(Pocket, related_name='crowdcoin_payment_lead_pocket_to')
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    identifiers = models.ManyToManyField(UniqueIdentifier, blank=True)
    reference = models.CharField(max_length=150, blank=True, null=True)
    transactions = models.ManyToManyField(Transaction, related_name="crowdcoin_payment_lead_transactions", blank=True)
    status = models.CharField(max_length=100, default="Pending", choices=(("Pending", "Pending"),
                                                                          ("Accepted", "Accepted"),
                                                                          ("Declined", "Declined"),
                                                                          ("Canceled", "Canceled")))
    created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    item_name = models.CharField(max_length=150, blank=True, null=True)
    item_description = models.CharField(max_length=150, blank=True, null=True)
    return_url = models.CharField(max_length=150, blank=True, null=True)
    notify_url = models.CharField(max_length=150, blank=True, null=True)
    cancel_url = models.CharField(max_length=150, blank=True, null=True)   
    airtime_deposit_lead = models.ForeignKey(AirtimeDepositLead, related_name='airtime_deposit_lead', null=True, blank=True)

    def __unicode__(self):
        return "%s to %s : %s" % (self.pocket_from, self.pocket_to, self.amount)


class BankPaymentLead(models.Model):
    pocket = models.ForeignKey(Pocket, related_name='bank_payment_lead_pocket')
    bank = models.CharField(max_length=150, blank=True, null=True)
    branch_code = models.CharField(max_length=150, blank=True, null=True)
    account_no = models.CharField(max_length=150, blank=True, null=True)
    reference = models.CharField(max_length=150, blank=True, null=True)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    identifiers = models.ManyToManyField(UniqueIdentifier, blank=True)
    transactions = models.ManyToManyField(Transaction, related_name="bank_payment_lead_transactions", blank=True)
    status = models.CharField(max_length=100, default="Pending", choices=(("Pending", "Pending"),
                                                                          ("Accepted", "Accepted"),
                                                                          ("Declined", "Declined"),
                                                                          ("Canceled", "Canceled")))
    created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return "%s to %s : %s" % (self.pocket, self.reference, self.amount)


class VoucherPaymentLead(models.Model):
    sender_name = models.CharField(max_length=150, blank=True, null=True)
    recipient_name = models.CharField(max_length=150, blank=True, null=True)
    sender_msisdn = models.CharField(max_length=150, blank=True, null=True)
    recipient_msisdn = models.CharField(max_length=150, blank=True, null=True)
    voucher_code = models.CharField(max_length=150, blank=True, null=True)
    security_pin = models.CharField(max_length=150, blank=True, null=True)
    days_valid = models.IntegerField(default=7, blank=True, null=True)
    amount = models.FloatField(default=0,blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True, default="ZAR")
    pocket_from = models.ForeignKey(Pocket, blank=True, null=True, related_name='voucher_payment_lead_pocket_from')
    pocket_to = models.ForeignKey(Pocket, blank=True, null=True, related_name='voucher_payment_lead_pocket_to')
    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100, default="Pending", choices=(("Awaiting Collection", "Awaiting Collection"),
                                                                          ("Collected", "Collected"),
                                                                          ("Pending", "Pending"),
                                                                          ("Declined", "Declined"),
                                                                          ("Canceled", "Canceled")))
    active = models.BooleanField(default=True)

    def __unicode__(self):
        return "%s : %s %s" % (self.voucher_code, self.amount, self.currency)


class SmsTemplate(models.Model):
    name = models.CharField(max_length=150, blank=True, null=True)
    identifiers = models.ManyToManyField(UniqueIdentifier, blank=True)
    description = models.CharField(max_length=150, blank=True, null=True)
    content = models.TextField(max_length=160,blank=True,null=True)

    def __unicode__(self):
        return "%s: %s" % (self.name,self.description)


class OneTimePin(models.Model):
    address = models.CharField(max_length=20,null=True)
    pin = models.CharField(max_length=10)
    created = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=False, blank=True)

    def __unicode__(self):
        return self.pin        


#===========================================================================
# SIGNALS
#===========================================================================


def signals_import():
    """ A note on signals.
    The signals need to be imported early on so that they get registered
    by the application. Putting the signals here makes sure of this since
    the models package gets imported on the application startup.
    """
    from tastypie.models import create_api_key
    from website.utils import send_transaction_sms
    from website.tasks import post_save_verifyid,\
        create_transaction,crowdcoin_payment_transaction,\
        bank_payment_transaction,voucher_payment_transaction,send_outbound_sms,update_crowdcoin_airtime_lead

    models.signals.post_save.connect(create_api_key, sender=User)
    models.signals.post_save.connect(send_transaction_sms, sender=Transaction,weak=True)
    models.signals.post_save.connect(post_save_verifyid, sender=UserProfile, weak=False)
    #models.signals.post_save.connect(create_transaction, sender=AirtimeDepositLead, weak=False)
    models.signals.post_save.connect(crowdcoin_payment_transaction, sender=CrowdcoinPaymentLead, weak=False)
    models.signals.post_save.connect(update_crowdcoin_airtime_lead, sender=AirtimeDepositLead, weak=False)
    models.signals.post_save.connect(bank_payment_transaction, sender=BankPaymentLead, weak=False)
    models.signals.post_save.connect(voucher_payment_transaction, sender=VoucherPaymentLead, weak=False)
    models.signals.post_save.connect(send_outbound_sms, sender=SmsOutBound, weak=False)
    # models.signals.m2m_changed.connect(send_transaction_sms, sender=Transaction.identifiers)

signals_import()
