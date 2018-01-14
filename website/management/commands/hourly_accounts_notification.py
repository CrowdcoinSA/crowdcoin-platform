from django.core.management.base import BaseCommand, CommandError
from website.utils import send_sms,get_user_available_balance
from django.contrib.auth.models import User
from website.models import DepositLead,UserProfile,FundsTransaction,SimCard
from datetime import datetime,timedelta
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            logger.info("Sending hourly notifications")
            accounts_profile = UserProfile.objects.get(user__email="accounts@crowdcoin.co.za")
            time_end=datetime.now()
            time_start=time_end + timedelta(hours=-1)
            #Update profile balance
            '''profiles= UserProfile.objects.all()
            for profile in profiles:
                profile.balance= get_user_available_balance(profile.user.username)
                profile.save()
            '''
            #Activate on hold transactions
            transactions = FundsTransaction.objects.filter(on_hold=True,hold_expire__lte=time_end,hold_expire__gte=time_start,)
            for transaction in transactions:
                transaction.status="Completed"
                transaction.on_hold=False
                transaction.save()

            deposit_leads=DepositLead.objects.filter(created__lte=time_end,created__gte=time_start,status="Active")
            funds_transactions=FundsTransaction.objects.filter(datetime__lte=time_end,datetime__gte=time_start,status="Pending")
            '''
            sims = SimCard.objects.filter(status="Receiving")
            sims_dict={}
            for sim in sims:
                try:
                    sims_dict[sim.network.name] +=1
                except KeyError,e:
                    sims_dict[sim.network.name] = 1
            '''
            if len(deposit_leads)>0 or len(funds_transactions)>0:
                message="Crowdcoin hourly notification-Deposit leads: %s\nFunds transactions: %s\nCompleted: %s" % (len(deposit_leads),len(funds_transactions),len(transactions))
                #send_sms(message,accounts_profile)
                send_sms(message,msisdn='27719535974') #notify melita
                send_sms(message,msisdn='27604162584') #notify kuli
                #send_mail("Hourly Notification",message,'Crowdcoin Admin',[accounts_profile.user.email],fail_silently=False)
            else:
                logger.info("No notifications to send")


        except Exception,e:
            logger.warning(e)
