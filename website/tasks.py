from __future__ import absolute_import, unicode_literals
import logging
import os
from django.db import transaction
from django.conf import settings  
from django.utils.crypto import get_random_string
from django.conf import settings
from datetime import datetime, timedelta, time
from celery.task.schedules import crontab
from celery.decorators import periodic_task
from celery import Celery
import requests

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crowdcoincoza.settings')

app = Celery('tasks')


app.conf.update(BROKER_URL=os.environ.get('REDIS_URL',"redis://"),
                CELERY_RESULT_BACKEND=os.environ.get('REDIS_URL','redis://'),
                # CELERYBEAT_SCHEDULE = {
                # 'add-every-30-seconds': {
                #     'task': 'tasks.allocate_airtime_to_lead',
                #     'schedule': timedelta(seconds=30),
                #     'args': (16, 16)
                # }
                # }
                )



#TODO:properly setup celery
@app.task
def post_save_verifyid(sender,*args, **kwargs):
    from website.models import Pocket, Merchant
    def on_commit():
        profile = kwargs.get('instance')
        #Create default Pocket
        default_pocket = Pocket.objects.get_or_create(name="{username}'s default Pocket".format(username=profile.user.username),tag=profile.user.username)[0]
        profile.pockets.add(default_pocket)
        #Create Airtime Trading Pocket
        #airtime_trading_pocket = Pocket.objects.get_or_create(name='Airtime Investment Pocket', tag="AI{username}".format(username=profile.user.username))[0]
        #profile.pockets.add(airtime_trading_pocket)
        if not profile.default_pocket:
            profile.default_pocket = default_pocket
            profile.save()

        #Create Merchant
        merchant = Merchant.objects.get_or_create(
            profile = profile,
            trading_name = profile.display_name,
            email = profile.user.email,
            default_pocket = profile.default_pocket)

    transaction.on_commit(on_commit)

@app.task
def create_transaction(sender,*args,**kwargs):
    from website.models import Transaction,UserProfile,Pocket,UniqueIdentifier,AirtimeDepositLead
    def on_commit():
        instance = kwargs.get('instance')
        if instance :
            if instance.status == "Accepted":
                transaction_tag = "airtime_deposit_{id}".format(id=instance.id)
                if Transaction.objects.filter(identifiers__value=transaction_tag).exists():
                    transaction = Transaction.objects.filter(identifiers__value=transaction_tag).delete()

                transaction = Transaction.objects.create(
                    debit=False,
                    pocket=instance.pocket,
                    amount=instance.amount,
                    datetime=datetime.now()
                )

                if not UniqueIdentifier.objects.filter(name="transaction_tag",
                                                   value="airtime_deposit_{id}".format(id=instance.id)
                                                   ).exists():

                    tag = UniqueIdentifier.objects.create(name="transaction_tag",
                                                       value="airtime_deposit_{id}".format(id=instance.id))

                tag = UniqueIdentifier.objects.get(name="transaction_tag",
                                                   value="airtime_deposit_{id}".format(id=instance.id))

                if not UniqueIdentifier.objects.filter(name="transaction_type",
                                                   value="airtime_deposit"
                                                   ).exists():
                    transaction_type = UniqueIdentifier.objects.create(name="transaction_type",
                                                   value="airtime_deposit")

                transaction_type = UniqueIdentifier.objects.get(name="transaction_type",
                                                             value="airtime_deposit"
                                                             )

                transaction.identifiers.update()
                instance.identifiers.add(tag)
                transaction.identifiers.add(transaction_type)
                instance.identifiers.add(transaction_type)

                for identifier in instance.identifiers.all():
                    print identifier
                    transaction.identifiers.add(identifier)

                instance.transactions.add(transaction)

                # Update SIM actual balance
                sim = instance.sim_card
                if sim:
                    sim.balance_month += sim.balance_day
                    if sim.balance_day < sim.network.daily_limit:
                        if sim.balance_month < sim.network.airtime_transfer_limit:
                            sim.status = "Receiving"
                    sim.save()

                transaction.save()
                return True
            elif instance.status in ["Declined", "Canceled"]:
                for transaction in instance.transactions.all():
                    transaction.active = False
                    transaction.save()

    transaction.on_commit(on_commit)

@app.task
def crowdcoin_payment_transaction(sender,*args,**kwargs):
    from website.models import Transaction,UserProfile,Pocket,UniqueIdentifier,AirtimeDepositLead
    from website.utils import send_sms
    def on_commit():
        instance = kwargs.get('instance')
        if instance:
            if instance.status == "Accepted":
                transaction_tag = "CC Payment #{id}".format(id=instance.id)
                if Transaction.objects.filter(identifiers__value=transaction_tag).exists():
                    transactions = Transaction.objects.filter(identifiers__value=transaction_tag)
                    for tran in transactions:
                        tran.delete()

                transaction_to = Transaction.objects.create(
                    debit=False,
                    pocket=instance.pocket_to,
                    amount=instance.amount,
                    datetime=datetime.now()
                )
                transaction_from = Transaction.objects.create(
                    debit=True,
                    pocket=instance.pocket_from,
                    amount=instance.amount,
                    datetime=datetime.now()
                )


                tag = UniqueIdentifier.objects.get_or_create(name="transaction_tag",
                                                   value=transaction_tag)[0]
                reference = UniqueIdentifier.objects.create(name="reference",
                                                             value=instance.reference)
                transaction_to.identifiers.add(tag)
                transaction_to.identifiers.add(reference)
                transaction_from.identifiers.add(tag)
                transaction_from.identifiers.add(reference)
                instance.identifiers.add(tag)
                instance.transactions.add(transaction_to)
                instance.transactions.add(transaction_from)

                #Notify parties
                try:
                    profiles_to = UserProfile.objects.filter(default_pocket=instance.pocket_to)
                    profiles_from = UserProfile.objects.filter(default_pocket=instance.pocket_from)

                    msg_credit = "(((C) Crowdcoin Funds Alert\n"\
                        "R {amount} credited to {pocket_tag}.\n"\
                        "Sign in at merchant.crowdcoin.co.za for more transaction details.".format(amount=instance.amount,pocket_tag=instance.pocket_to.tag)

                    msg_debit = "(((C) Crowdcoin Funds Alert\n"\
                        "R {amount} deducted from {pocket_tag}.\n"\
                        "Sign in at merchant.crowdcoin.co.za for more transaction details.".format(amount=instance.amount,pocket_tag=instance.pocket_from.tag)

                    for profile in profiles_to:
                        send_sms(msg_credit,profile.msisdn)

                    for profile in profiles_from:
                        send_sms(msg_debit,profile.msisdn)
                        
                except Exception as e:
                    logger.warning(e.message)

                # Notify Merchant URL
                try:
                    payload= {'reference': instance.reference,
                    'payment_status': instance.status,
                    'item_name':instance.item_name,
                    'amount':instance.amount,
                    'merchant_id': instance.pocket_to.tag
                    }                    
                    merchant_notif_response = requests.post(url= instance.notify_url, data=payload)
                    logger.info(merchant_notif_response.content)
                except Exception as e:
                    logger.warning(e.message)               

            elif instance.status in ["Declined", "Canceled"]:
                for transaction in instance.transactions.all():
                    transaction.active = False
                    transaction.save()

    transaction.on_commit(on_commit)


@app.task
def bank_payment_transaction(sender,*args,**kwargs):
    def on_commit():
        instance = kwargs.get('instance')
        if instance:
            if instance.status == "Accepted":
                transaction_tag = "bank_payment_{id}".format(id=instance.id)
                if Transaction.objects.filter(identifiers__value=transaction_tag).exists():
                    transactions = Transaction.objects.filter(identifiers__value=transaction_tag)
                    for tran in transactions:
                        tran.delete()

                transaction = Transaction.objects.create(
                    debit=True,
                    pocket=instance.pocket,
                    amount=instance.amount,
                    datetime=datetime.now()
                )


                tag = UniqueIdentifier.objects.get_or_create(name="transaction_tag",
                                                   value=transaction_tag)[0]
                transaction.identifiers.add(tag)
                instance.identifiers.add(tag)
                instance.transactions.add(transaction)

            elif instance.status in ["Declined", "Canceled"]:
                for transaction in instance.transactions.all():
                    transaction.active = False
                    transaction.save()

    transaction.on_commit(on_commit)


@app.task
def voucher_payment_transaction(sender,*args,**kwargs):
    from website.models import Transaction,UserProfile,Pocket,UniqueIdentifier,AirtimeDepositLead,VoucherPaymentLead
    from website.utils import send_sms
    def on_commit():
        instance = kwargs.get('instance')
        logger.info(instance.voucher_code)
        if instance:
            if instance.voucher_code in [None, ''] or len(instance.voucher_code) != 13:
                voucher_code = get_random_string(length=13,allowed_chars='123456789')
                while VoucherPaymentLead.objects.filter(voucher_code=voucher_code).exists():
                    voucher_code = get_random_string(length=13,allowed_chars='123456789')
                instance.voucher_code = voucher_code
                instance.save()
            # if instance.security_pin in [None, '']:
            #     instance.security_pin = get_random_string(length=4,allowed_chars='123456789')
            #     instance.save()
            if instance.status in ["Pending","Awaiting Collection","Collected"]:
                transaction_tag = "voucher purchase #{id}".format(id=instance.id)


                sender_tag = UniqueIdentifier.objects.get_or_create(name="Sender_tag",value=transaction_tag)[0]
                reciever_tag = UniqueIdentifier.objects.get_or_create(name="Reciever_tag",value=transaction_tag)[0]
                fee_tag = UniqueIdentifier.objects.get_or_create(name="Fee_tag",value="Fee "+transaction_tag)[0]
                commission_tag = UniqueIdentifier.objects.get_or_create(name="Commission_tag",value="Commission "+transaction_tag)[0]

                if instance.status == "Pending":
                    msg_sender = "(((C) Thank You\n" \
                        "Your R{amount} Crowdcoin Voucher is on the way.\n" \
                        "Please allow upto 60 minutes while we process your purchase.\n "\
                        "Track your voucher at www.crowdcoin.co.za/verify/{voucher_code} or dial *120*912*87#.".format(amount=instance.amount,voucher_code=instance.voucher_code)                    
                    send_sms(msg_sender,instance.recipient_msisdn)



                if instance.status == "Awaiting Collection":

                    Transaction.objects.filter(identifiers=sender_tag).delete()
                    Transaction.objects.filter(identifiers=fee_tag).delete()

                    transaction_from = Transaction.objects.create(
                        debit=True,
                        pocket=instance.pocket_from,
                        amount=instance.amount,
                        datetime=datetime.now()
                    )
                    logger.info(instance.pocket_from.voucher_sending_fee.strip('%'))
                    fee_from_amount = float(instance.amount) * float(instance.pocket_from.voucher_sending_fee.strip('%'))/100 if '%' in instance.pocket_from.voucher_sending_fee else float(instance.pocket_from.voucher_sending_fee)
                    logger.info("Fee %s"%fee_from_amount)
                    fee_from = Transaction.objects.create(
                        debit=True,
                        pocket=instance.pocket_from,
                        amount=fee_from_amount,
                        datetime=datetime.now()
                    )
                    
                    fee_from.identifiers.add(fee_tag)                    
                    transaction_from.identifiers.add(sender_tag)                    
                    #Send Voucher + Pin to recipient
                    # msg_recipient = "(((C) " \
                    #     "R{amount} Crowdcoin Money Transfer\n" \
                    #     "Voucher Code: {voucher_code}\n" \
                    #     "Security PIN: {voucher_security_pin}\n\nVisit http://help.crowdcoin.za for help.".format(amount=instance.amount,
                    #         voucher_security_pin='Ask {sender_name}'.format(sender_name=instance.sender_name),
                    #         voucher_code=instance.voucher_code)
                                                                                          
                    # send_sms(msg_recipient,instance.recipient_msisdn)

                    msg_sender = "(((C)  Voucher\nAmount: {amount}\n" \
                        "Pin: {voucher_code}\n" \
                        "Dial *129*912*87*87# to load your voucher.\n\nhelp.crowdcoin.za.".format(amount=instance.amount,
                            recipient_name=instance.recipient_name,
                            voucher_code=instance.voucher_code)                    
                    send_sms(msg_sender,instance.recipient_msisdn)

                if instance.status == "Collected":
                    Transaction.objects.filter(identifiers=reciever_tag).delete()
                    Transaction.objects.filter(identifiers=commission_tag).delete()

                    transaction_to = Transaction.objects.create(
                        debit=False,
                        pocket=instance.pocket_to,
                        amount=instance.amount,
                        datetime=datetime.now()
                    )
                    fee_to_amount = float(instance.amount) * float(instance.pocket_to.voucher_receiving_fee.strip('%'))/100 if '%' in instance.pocket_to.voucher_receiving_fee else float(instance.pocket_to.voucher_receiving_fee)
                    logger.info("Fee %s"%fee_to_amount)
                    fee_to = Transaction.objects.create(
                        debit=False,
                        pocket=instance.pocket_to,
                        amount=fee_to_amount,
                        datetime=datetime.now()
                    )

                    fee_to.identifiers.add(commission_tag)                       
                    instance.active = False
                    transaction_to.identifiers.add(reciever_tag)

                    #Send redeemption sms


            elif instance.status in ["Declined", "Canceled"]:
                for transaction in instance.transactions.all():
                    transaction.active = False
                    transaction.save()


    transaction.on_commit(on_commit)


@app.task
def send_outbound_sms(sender,*args,**kwargs):
    from website.utils import send_sms
    import urllib,json
    def on_commit(): 
        logger.info('Sending SMS') 
        try:  
            sms = kwargs.get('instance')
            if sms and not sms.is_dispatched:
                
                url = "https://api.panaceamobile.com/json?username={username}&password={password}&text={body}&to={recipient}&action=message_send&from={sender}".format(body=sms.message,
                    recipient=sms.msisdn,
                    sender="Crowdcoin",
                    username=settings.PANACEA_USER,
                    password=settings.PANACEA_PASSWORD)
                f = urllib.urlopen(url)
                s = json.loads(f.read())
                statusCode = s.get("status")
                statusString = s.get("message")
                if statusCode != '1':
                    dispatched=False
                else:
                    dispatched=True
                sms.is_dispatched=dispatched
                sms.status_string=statusString
                sms.status_code=statusCode
                #sms.save()
                f.close() 
            else:
             logger.info('SMS not sent') 
        except Exception as e:
            sms.is_dispatched=False
            logger.warning(e.message)
    transaction.on_commit(on_commit)        


@app.task
def update_crowdcoin_airtime_lead(sender,*args,**kwargs):
    from website.models import CrowdcoinPaymentLead
    def on_commit():
        instance = kwargs.get('instance')
        if instance:
            try:
                if instance.status in ["Accepted","Canceled","Pending"]:
                    logger.info("called update_crowdcoin_airtime_lead")
                    payment_lead = CrowdcoinPaymentLead.objects.get(airtime_deposit_lead__pk=instance.pk)
                    payment_lead.status = instance.status
                    payment_lead.save()

            except Exception as e:
                logger.warning(e.message)
    transaction.on_commit(on_commit)

@periodic_task(run_every=(crontab(minute='*/10')), name="allocate_airtime_to_lead", ignore_result=True)
def allocate_airtime_to_lead():

    logger.info("Allocating Airtime Deposit Transactions To Airtime Deposit Leads")
    from website.models import AirtimeDepositLead, SimCard,AirtimeDepositTransaction
    from django.db.models import Sum
    from django.utils import timezone
    now = timezone.now()
    logger.info(now)
    active_leads = AirtimeDepositLead.objects.filter(active=True,
        status='Pending')
    logger.info(active_leads)
    for lead in active_leads:
        sim_transactions = AirtimeDepositTransaction.objects.filter(sim_card=lead.sim_card,
            created__gte=lead.created)
        total_amount = sim_transactions.aggregate(Sum('amount'))['amount__sum']
        logger.info(total_amount)
        if lead.amount <= total_amount:
            for trans in sim_transactions:
                lead.airtime_deposit_transactions.add(trans)
            lead.status = 'Accepted'
        #Release expired transactions
        time_elapsed = datetime.combine(now, now.time())- datetime.combine(now, lead.created.time())
        logger.info("Time elapsed: {time_elapsed}".format(time_elapsed=time_elapsed))
        if time_elapsed > timedelta(minutes=15):
            logger.info("Cancelled Lead {lead}".format(lead=lead))
            lead.status = 'Canceled'
        lead.sim_card.status = "Receiving"
        lead.sim_card.save()
        lead.save()

    return

@periodic_task(run_every=(crontab(minute='*/15')), name="fetch_remote_sim_transactions", ignore_result=True)
def fetch_remote_sim_transactions():
    from website.models import SimCard
    from website.utils import process_vodacom_leads

    voda_sims = SimCard.objects.filter(is_active=True, network__name='Vodacom')
    logger.info("Fetching {total_sims} Sim Cards".format(total_sims=voda_sims.count()))
    for sim in voda_sims:
        process_vodacom_leads(cell_no=sim.msisdn, password=sim.online_password)
