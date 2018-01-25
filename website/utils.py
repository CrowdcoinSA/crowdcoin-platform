from website.models import *
from django.contrib.auth.models import User
from django.db.models import Sum
import random
import urllib
import logging
import json
import requests
import re
import os
from tastypie.models import ApiKey
from datetime import datetime, timedelta, time
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Context
from tastypie.models import ApiKey
from xhtml2pdf import pisa
from django import template
from freshdesk.api import API as FreshdeskApi
from django.conf import settings


register = template.Library()
logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def generate_source_id():
    while True:
        source_id=''
        while len(source_id)<10:
            n=random.randint(0,9)
            source_id+=`n`
        source_id = int(source_id)

        if not SmsOutBound.objects.filter(source_id=source_id).exists():
            break
    return source_id


def transaction_double_entry_hook(sender, **kwargs):
    """
       A signal for hooking up automatic ``double entry`` creation.
       """
    try:
        instance = kwargs.get('instance')
        double_entry_id_value = instance.identifiers.get(name='double_entry_identifier_value').value
        double_entry_id_type = instance.identifiers.get(name='double_entry_identifier_type').value

        if Pocket.objects.filter(identifiers__value=double_entry_id_value,identifiers__name=double_entry_id_type).exists():
            logger.info("Found matching Pocket")
            pocket = Pocket.objects.get(identifiers__name=double_entry_id_type,identifiers__value=double_entry_id_value)
            print pocket
        else:
            #Flag transaction when no matching double entry key exists
            logger.info("Matching Pocket Not Found")
            logger.info(instance.identifiers.all())
            instance.identifiers.add(name="flag",value="double_entry_not_found")
            logger.info(instance)
    except Exception as e:
        pass


def assign_default_pocket_hook(profile):
    from website.models import UserProfile
    logger.info(kwargs)
    if profile:
        if profile.pockets.all().count == 0:
            identifier = UniqueIdentifier.objects.create(name="account_type",value="private")
            profile.pockets.add(
                name=profile.user.username,
                identifiers=identifier
            )
            profile.default_pocket = profile.pockets.last()
            profile.save()
            logger.info("Created")
        elif not profile.default_pocket:
            profile.default_pocket = profile.pockets.last()
            profile.save()
            logger.info("Assigned")
            
    return 



def send_sms(message,msisdn):
    from website.models import SmsOutBound

    sms = SmsOutBound.objects.get_or_create(msisdn=msisdn,message=message)

    return


def register_new_user(*args,**kwargs):
    from website.models import UserProfile
    from django.contrib.auth.models import User
    try:
        logger.info(kwargs)
        logger.info(args)
        if len(args) > 0:
            profile = args[0]
        else:
            profile = kwargs
        user = User.objects.get_or_create(
            username=profile.get('username'))[0]
        user.first_name = profile.get('first_name', '')
        user.last_name = profile.get('last_name', '')

        if profile.get('raw_password'):
            user.set_password(profile.get('raw_password'))
            user.save()

        userProfile = UserProfile.objects.get_or_create(user=user)[0]
        userProfile.identification_country = profile.get('identification_country', 'ZA')
        userProfile.identification_no = profile.get('identification_no', '0000000000000')
        userProfile.identification_type = profile.get('identification_type', 'ID')
        userProfile.network = profile.get('network')
        userProfile.pin = profile.get('pin', '0000')
        userProfile.msisdn = profile.get('msisdn')
        userProfile.referrer = profile.get('referrer')
        userProfile.save()

        response = {"status":"success","message":"Registration successful","results":userProfile}
        return response

    except Exception as e:
        logger.warning(e)
        return {"status":"error","message":"Registration failed","results":None}




def send_reg_email(email_address,full_names,username,password):


    try:
        plaintext = get_template('email/welcome-account.txt')
        htmly     = get_template('email/welcome-account.html')

        d = Context({ 'username': username, 'password':password,"full_names":full_names,"email_address":email_address,"api_key":ApiKey.objects.get(user__username=username).key })

        subject, from_email, to = '%s, Welcome To Crowdcoin' % full_names, 'Crowdcoin Support', email_address
        text_content = plaintext.render(d)
        html_content = htmly.render(d)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

    except Exception,e:
        logger.error(e)


MINIMUM_PASSWORD_LENGTH = 4
REGEX_VALID_PASSWORD = (
    ## Don't allow any spaces, e.g. '\t', '\n' or whitespace etc.
    r'^(?!.*[\s])'
    ## Check for a digit
    '((?=.*[\d])'
    ## Check for an uppercase letter
    #'(?=.*[A-Z])'
    ## check for special characters. Something which is not word, digit or
    ## space will be treated as special character
    '(?=.*[^\w\d\s])).'
    ## Minimum 8 characters
    '{' + str(MINIMUM_PASSWORD_LENGTH) + ',}$')


def validate_password(password):
    if re.match(REGEX_VALID_PASSWORD, password):
        return True
    return False


def convertHtmlToPdf(sourceHtml, outputFilename,fail_silently=True):
    try:

        # open output file for writing (truncated binary)
        resultFile = open(outputFilename, "w+b")

        # convert HTML to PDF
        pisaStatus = pisa.CreatePDF(
                sourceHtml,                # the HTML to convert
                dest=resultFile,
                raise_exception=fail_silently,
        )

        # close output file
        resultFile.close()                 # close output file
        # return True on success and False on errors
        return pisaStatus.err
    except Exception,e:
        logger.warning(e)


def email_admin_summary(account_no=None,recipients=['billing@crowdcoin.co.za'], period='yesterday',send_email=True):
    if period == "yesterday":
        today = datetime.now().date()
        yesterday = today - timedelta(1)
        yesterday_end = datetime.combine(yesterday, time(hour=23,minute=59))
        yesterday_start = datetime.combine(yesterday, time())
        period = {"start":yesterday_start,"end":yesterday_end}
    if account_no == None:
        account_no = "Admin"
        user_profile = UserProfile.objects.get(user__username='admin')
        opening_balance = get_user_available_balance(ending=period['start'])
        closing_balance = get_user_available_balance(ending=period['end'])
        #Deposit leads
        user_profile = UserProfile.objects.get(user__username='admin')
        deposit_leads = []# DepositLead.objects.filter(created__gte=period["start"],created__lte=period['end']).order_by('created')
        funds_transactions = FundsTransaction.objects.filter(datetime__gte=period["start"],datetime__lte=period['end']).order_by('datetime')
    else:
        user_profile = UserProfile.objects.get(account_no=account_no)
        opening_balance = get_user_available_balance(ending=period['start'],username=user_profile.user.username)
        closing_balance = get_user_available_balance(ending=period['end'],username=user_profile.user.username)
        #Deposit leads
        deposit_leads = []#DepositLead.objects.filter(profile=user_profile,created__gte=period["start"],created__lte=period['end']).order_by('created')
        funds_transactions = FundsTransaction.objects.filter(profile=user_profile,datetime__gte=period["start"],datetime__lte=period['end']).order_by('datetime')
    #Bundle up summary
    summary = {'deposit_leads':deposit_leads,
               'period':period,
               "funds_transactions":funds_transactions,
               "user_profile":user_profile,
               "opening_balance":opening_balance,
               "closing_balance":closing_balance}
    try:
        if account_no == "Admin":
            plaintext = get_template('email/daily-summary.txt')
            htmly     = get_template('email/daily-summary.html')
        else:
            plaintext = get_template('email/daily-summary.txt')
            htmly     = get_template('email/statement mail.html')
        pdf = get_template('email/statement template.html')

        d = Context({ 'summary':summary,'statement':summary })
        subject = '%s :D - Crowdcoin Statement for %s' % (user_profile.user.first_name, account_no)
        file_name = 'Statement %s-%s.pdf' % (account_no,period["end"].month)
        from_email =  'Crowdcoin Reports'
        text_content = plaintext.render(d)
        html_content = htmly.render(d)
        pdf_content = pdf.render(d)
        convertHtmlToPdf(pdf_content,file_name)
        if send_email is True:
            msg = EmailMultiAlternatives(subject, text_content, from_email, recipients)
            msg.attach_file(file_name,'application/pdf')
            msg.attach_alternative(html_content, "text/html")
            msg.send()

    except Exception,e:
        logger.error(e)

def migrate_patch():
    try:
        if not Location.objects.filter(country_name="South Africa").exists():
            za=Location.objects.create(country_name="South Africa",country_code="ZA",currency="ZAR")
        else:
            za=Location.objects.get(country_name="South Africa")
        for profile in UserProfile.objects.all():
            profile.account_no=profile.msisdn
            profile.country=za
            profile.price_plan="Platinum"
            profile.save()


    except Exception,e:
        logger.info(e)

class TokenAuthenticationMiddleware(object):
    def authenticate(self, username=None,token=None):
        print "Custom authentication - %s - %s" %(username,token)
        if ApiKey.objects.filter(user__username=username,key=token).exists():
            user = User.objects.get(username=username)
            print "returning", str(user)
            return user
        else:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

def mass_mail_statements():
    profiles = UserProfile.objects.filter().exclude(user__email__isnull=True).exclude(user__email__exact='')
    for profile in profiles:
        start = datetime(month=10,year=2015,day=1)+timedelta(0)
        end = datetime(month=10,year=2015,day=30)+timedelta(0)
        email_admin_summary(account_no=profile.account_no,
                            recipients=[profile.user.email],
                            send_email=True,
                            period={'start':start,'end':end})
    logger.info("Mailed %s" % len(profile))


def mail_promo(user_profile=None,send_email=True):
    if user_profile is None:
        profiles = UserProfile.objects.filter().exclude(user__email__isnull=True).exclude(user__email__exact='')
    else:
        profiles = [user_profile]
    for user_profile in profiles:
        try:
            recipient = [user_profile.user.email]
            plaintext = get_template('email/promotions/Free Upgrade + #ULTRA2016 Tickets. With love, Crowdcoin..txt')
            htmly     = get_template('email/promotions/Free Upgrade + #ULTRA2016 Tickets. With love, Crowdcoin..html')

            d = Context({ 'user_profile':user_profile })
            subject = 'Free Upgrade + #ULTRA2016 Tickets. With love, Crowdcoin.'
            from_email =  'Kearabiloe Ledwaba - Crowdcoin CEO'
            text_content = plaintext.render(d)
            html_content = htmly.render(d)
            if send_email is True:
                msg = EmailMultiAlternatives(subject, text_content, from_email, recipient)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

        except Exception,e:
            logger.error(e)




def freshdesk_new_ticket(name,subject, description, email=None, phone=None,company=None,priority=1, status=2,source=2):
    freshdesk_api = FreshdeskApi(settings.FRESHDESK_URL, settings.FRESHDESK_KEY, version=2)


    ticket = freshdesk_api.tickets.create_ticket(subject,
        description=description,
        email=email,
        phone=phone,
        name=name,
        company=company,
        type='Lead',
        responder_id=6003130775,
        priority=priority)

    logger.warning(ticket)
    return

def ProcessEmailTransaction():
    #TODO: Clean and optimize function
    import sys
    import imaplib
    import email
    import email.header
    import datetime

    EMAIL_ACCOUNT = ""
    EMAIL_FOLDER = "Deposits"
    EMAIL_PASSWORD = ""


    def process_mailbox(M):
        try:
            """
            Do something with emails messages in the folder.
            For the sake of this example, print some headers.
            """

            rv, data = M.search(None, 'SUBJECT', "Forwarded Message")
            if rv != 'OK':
                logger.error("No messages found!")
                return

            for num in data[0].split():
                rv, data = M.fetch(num, '(RFC822)')
                if rv != 'OK':
                    logger.error("ERROR getting message %s" % num)
                    return

                msg = email.message_from_string(data[0][1])
                decode = email.header.decode_header(msg['Subject'])[0]
                subject = unicode(decode[0])
                body = msg.get_payload(decode=True)
                #print 'Raw Date:', msg['Date']
                # Now convert to local date-time
                date_tuple = email.utils.parsedate_tz(msg['Date'])
                if date_tuple:
                    local_date = datetime.datetime.fromtimestamp(
                        email.utils.mktime_tz(date_tuple))
                    # print "Local Date:", \
                    #     local_date.strftime("%a, %d %b %Y %H:%M:%S")
                if not EmailTransaction.objects.filter(received=local_date).exists():
                    if "Forwarded Message from MTN141" == subject and body not in ['',None]:
                        #Check if MTN airtime transfered to crowdcoin
                        if "sent from" in body:
                            body = body.split(".New")
                            body = body[0].split(" sent from ")
                            amount = float(body[0].strip("R"))
                            sender = body[1]

                            #Create Funds Transaction
                            if  UserProfile.objects.filter(user__username=sender).exists():

                                #Register Email
                                EmailTransaction.objects.create(
                                    email_id=num,
                                    subject=subject,
                                    body=body,
                                    received=local_date,
                                )

                                FundsTransaction.objects.create(
                                    profile=UserProfile.objects.get(user__username=sender),
                                    amount=amount,
                                    network = Network.objects.get(name="MTN"),
                                    transaction_type=TransactionType.objects.get(name="Airtime Deposit"),
                                    description=sender,
                                    status="Approved",
                                )

        except Exception as e:
            logger.warning(e)




    M = imaplib.IMAP4_SSL('imappro.zoho.com')

    try:
        rv, data = M.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    except imaplib.IMAP4.error:
        logger.error("LOGIN FAILED!!!")
        sys.exit(1)

    print rv, data

    rv, mailboxes = M.list()
    if rv == 'OK':
        pass

    rv, data = M.select(EMAIL_FOLDER)
    if rv == 'OK':
        process_mailbox(M)
        M.close()
    else:
        logger.error(("ERROR: Unable to open mailbox ", rv))

    M.logout()

def process_vodacom_leads(cell_no,password):
    import urllib
    import requests
    from dateutil.parser import parse
    from website.models import AirtimeDepositLead,AirtimeDepositTransaction, SimCard

    if cell_no[0] == '0':
        msisdn = "27"+cell_no[1:]
        cell_no = cell_no
    else:
        msisdn = cell_no
        cell_no = "0"+cell_no[2:]


    url_login = 'https://myvodacom.secure.vodacom.co.za/rest/services/v1/context/loginUser/'+cell_no   
    url_statement = '   https://myvodacom.secure.vodacom.co.za/rest/services/v1/statement/rechargehistory/'+cell_no
    logger.info("Processing SIM: {msisdn}, {cell_no}".format(msisdn=msisdn,cell_no=cell_no))
    sim = SimCard.objects.get(msisdn__in=[msisdn,cell_no])
    logger.info("Processing Sim: %s" % sim)

    request = requests.Session()
    headers = {'Content-type': 'application/x-www-form-urlencoded','Referer':'https://myvodacom.secure.vodacom.co.za/vodacom/log-in'}
    body = { 'password':password, 'referer':'','mobile':'false','currentUrl':'https://myvodacom.secure.vodacom.co.za/vodacom/log-in'}
    #Login
    response=request.post(url_login,urllib.urlencode(body),headers=headers)
    logger.info(response.content)
    if response.json()['successfull']:
        print "logged in"
        #Get statement
        response=request.post(url_statement,urllib.urlencode(body),headers=headers)
        if response.json()['successfull']:
            last_trans=response.json()['rechargeHistoryList']
            if len(last_trans) > 0 :
                for transaction in last_trans:
                    if not AirtimeDepositTransaction.objects.filter(reference = transaction['rechargeId']).exists():
                        airtime_transaction = AirtimeDepositTransaction.objects.get_or_create(reference = transaction['rechargeId'],
                            amount = transaction['amountRequested']['value'],
                            description = transaction['rechargeType'],
                            expiary_date = transaction['airtimeWindowEndDate'],
                            created = transaction['rechargeRequestDate'],
                            sim_card = sim
                            )
                        logger.info(airtime_transaction)
    else:
        logger.warning("Remote Sim Login Failed: {msisdn}".format(msisdn=msisdn))

def thisisme_id_check(identity_number,country_code='ZA',username=None,identity_type="ID"):
    from website.models import UserProfile

    try:
        url = 'https://uat.api.thisisme.com/id_check'
        data={'identity_number':identity_number,'country_code':country_code,'identity_type':identity_type}
        try:
            response = requests.get(
                url,
                cert=(
                    os.path.join(BASE_DIR,'configs/production/thisismecerts/fromthem/crowdcoin.co.za.pem'),
                    os.path.join(BASE_DIR,'configs/production/thisismecerts/www.crowdcoin.co.za.plainkey.pem')),
                verify=False,
                params=data)
        except Exception as e:
            return {'response': "An error occured while verifying your Identity. Please check the supplied information and try again.", 'status': 'error'}
        logger.info(response.text)
        response = response.json()
        
        logger.info(response.get('response'))
        status = response.get('status')
        if status == 'SUCCESS':
            response_data = response.get('response')
            if username  is not None:
                user_profile = UserProfile.objects.get(user__username=username)
                user_profile.user.first_name = response_data.get('firstnames')
                user_profile.user.last_name = response_data.get('surname')
                user_profile.identification_no = identity_number
                user_profile.identification_country = country_code
                user_profile.identification_type = response_data.get('identity_type')
                user_profile.gender = response_data.get('gender')
                user_profile.d_o_b = response_data.get('date_of_birth')
                user_profile.vital_status = response_data.get('vital_status')
                user_profile.is_verified= True
                user_profile.user.save()
                user_profile.save()
            return {'response':response_data,'status':'success'}
        else:
            return {'response': response['response']['description'], 'status': 'success'}
    except Exception, e:
        logger.error(e.message)
        return {'response':response,'status':'error'}
        
def get_user_available_balance(username=None,ending=None):
    try:
        logger.debug(username)
        if username is not None:
            user_profile = UserProfile.objects.get(user__username=username)
        if ending is not None:
            if username is None:
                funds_transactions = FundsTransaction.objects.filter(datetime__lte=ending)
            else:
                funds_transactions = FundsTransaction.objects.filter(profile=user_profile,datetime__lte=ending)
        else:
            funds_transactions = FundsTransaction.objects.filter(profile=user_profile).order_by("datetime")
        debits =funds_transactions.filter(status__in=["Approved","Pending","Awaiting Authorisation","Completed"],transaction_type__action="Debit").aggregate(Sum('amount'))
        credits =funds_transactions.filter(status__in=["Approved","Pending","Awaiting Authorisation","Completed"],transaction_type__action="Credit").aggregate(Sum('amount'))
        fees =funds_transactions.filter(status__in=["Approved","Pending","Awaiting Authorisation","Completed"]).aggregate(Sum('fee'))
        if credits.get('amount__sum') == None:
            credits['amount__sum'] = 0
        if debits.get('amount__sum') == None:
            debits['amount__sum'] = 0
        if fees.get('fee__sum') == None:
            fees['fee__sum'] = 0
        available_balance = credits.get('amount__sum')-(debits.get('amount__sum')+fees.get('fee__sum'))
        return available_balance
    except Exception,e:
        logger.info(e)


def prepare_sim_deposit(amount,network):
    #Todo: Redo completely
    logger.info("Preparing sim cards")
    amount = float(amount)
    from website.models import Network,SimCard
    if Network.objects.filter(name=network).exists():
        network = Network.objects.get(name=network)

        sims = SimCard.objects.filter(
                balance_day__lte=float(network.daily_limit-amount),
                network=network,
                status="Receiving")

        if sims.exists():
            sim = sims.last()
            logger.info(sim)
            sim.status = "Paused"
            sim.save()
            return {"status": "success", "message": sim, "code": "found"}
        else:
            return {"status": "error", "message": "Sim card not found.", "code": "not_found"}
        

    else:
        return {"status":"error","message":"Network not found.","code":"not_found"}


def send_transaction_sms(sender,**kwargs):
    from website.models import SmsTemplate,UserProfile,Transaction

    if kwargs.get('instance'):
        transaction = Transaction.objects.get(pk=kwargs.get('instance').pk)
        transaction_types = transaction.identifiers.all()#.filter(name="transaction_type")
        sms_templates = SmsTemplate.objects.filter(identifiers__in=transaction_types)
        reference = transaction.identifiers.filter(name__in=['transaction_reference']).last()
        recipients = UserProfile.objects.filter(pockets__in=[transaction.pocket])

        for sms_template in sms_templates:
            #Loop through all linked trasnctions types and send templated sms
            message = sms_template.content.format(
                amount=transaction.amount,
                reference=reference.value,
                pocket=transaction.pocket.name)

            for recipient in recipients.filter(identifier__name="msisdn"):

                for msisdn in recipient.identifier.all():
                    send_sms(message,msisdn.value)

