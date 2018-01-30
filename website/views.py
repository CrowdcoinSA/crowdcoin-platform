from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from website.utils import  *
from website.custom_context_processors import *
from django.contrib.auth import authenticate
import logging,csv
from django.http import JsonResponse
from django.utils.crypto import get_random_string
import xml.etree.ElementTree as ET
import decimal
import random

logger = logging.getLogger(__name__)
networks_to_dict={1:"Mtn",2:"Vodacom",4:"Cell C",3:"Telkom Mobile"}


def LandingView(request):
    response = "It works!"
    return HttpResponse(response)


def loaderio(request):
    response = 'loaderio-b193a2f576f0426fef58ef4dbe597971'
    return HttpResponse(response)


def support_ticket_create(request):
    try:
        description = "Full names: %s \nEmail: %s \nPhone no.: %s \nDescription: %s" % (request.GET.get("name"),
                                                                                        request.GET.get("email"),
                                                                                        request.GET.get("phone"),
                                                                                        request.GET.get("detail"))
        freshdesk_new_ticket(
            name=request.GET.get("name"),
            description=description,
            email=request.GET.get("email"),
            phone=request.GET.get("phone"),
            subject="MERCHANT REGISTRATION"
        )
        response = "<p>Thank you! We will be in touch.</p>"
    except Exception as e:
        logger.error(e)
        response = "<p>Sorry, We are having a problem saving your registration. Please reload the page and try again.</p>"
    return HttpResponse(response)


def ussdView(request):
    try:
        logger.debug(request.GET)
        msisdn = request.GET.get('ussd_msisdn')
        node_name = request.GET.get("ussd_node_name")
        network = request.GET.get("ussd_network_name")
        ussd_request = request.GET.get("ussd_request")
        # try:
        #     ussd_request_args = ussd_request.strip("#").split(settings.CROWDCOIN_USSD_STRING[:-1],1)[1][1:].split("*")
        # except Exception as e:
        #     logger.debug(e.message)
        #     ussd_request_args = ussd_request
        # logger.debug(settings.CROWDCOIN_USSD_STRING)
        # logger.debug(ussd_request)
        # logger.debug(ussd_request_args)
        #Replace country code
        msisdn = '0'+str(msisdn[2:])
        user = User.objects.get_or_create(username=msisdn)[0]
        userProfile = UserProfile.objects.get_or_create(user=user, msisdn=user.username)[0]


        if node_name == "Menu":
            logger.debug("Called Menu")
            merchant_id = None
            # if len(ussd_request_args) > 1:
            #     merchant_id = int(ussd_request_args[0])
            #     amount = int(ussd_request_args[1])

                # logger.debug(merchant_id)
                # logger.debug(amount)



            if merchant_id and Merchant.objects.filter(id=merchant_id).exists():
                merchant = Merchant.objects.get(id=merchant_id)
                response = "(((C) {merchant_name} \n\n" \
                           "You are about to pay  R {amount} using airtime.\n" \
                           "Please enter your reference:\n" \
                           "Example: INV123\n\n" \
                           "0. Help.\n".format(merchant_name=merchant.trading_name,amount=amount)

            else:
                merchant = Merchant.objects.all()
                response="(((C) Crowdcoin\n\n" \
                         "You have entered an invalid Merchant ID.\n\n" \
                         "1. Find Merchant ID\n" \
                         "0. Help\n" 
            return HttpResponse(response)

        if str(node_name).startswith("FindMerchantResults"):
            logger.debug("Called Find Merchant Results")
            if Merchant.objects.filter(trading_name__icontains=request.GET.get("ussd_response_FindMerchantKeyword")).exists():
                merchants = Merchant.objects.filter(trading_name__icontains=request.GET.get("ussd_response_FindMerchantKeyword"))
                merchants_string = "(((C) Merchants Found\n\n"
                if len(merchants)>=1:
                    for merchant in merchants:
                        merchants_string += "{merchant_id}={merchant_name}\n".format(merchant_id=merchant.id,merchant_name=merchant.trading_name)
                    response = merchants_string

                else:
                    response = "You do not have any pockets linked to your account"
            else:
                response = "(((C) Crowdcoin\n\n" \
                           "Use of service subject to Ts & Cs avaible at http://www.crowdcoin.co.za/legals.\n\n" \
                           "7. Join Crowdcoin for Business"
            return HttpResponse(response)                 

        if node_name == "Mini_Statement":
            profile = UserProfile.objects.get(user__username=msisdn)
            pocket = profile.pockets.filter(active=True).order_by('created')[int(request.GET.get("ussd_response_Active_Pocket_"+node_name))-1]
            transactions = Transaction.objects.filter(pocket=pocket,active=True).order_by('-datetime')[:10]
            transactions_tracker = 0
            transactions_string = "(((C) Mini Statement\n\n"
            if len(transactions)>0:
                for transaction in transactions:
                    transactions_tracker += 1
                    if transaction.debit:
                        credit_tag="-"
                    else:
                        credit_tag="+"
                    description = transaction.identifiers.get(name='transaction_tag').value
                    if description.startswith('voucher_payment'):
                        voucher = VoucherPaymentLead.objects.get(voucher_code =description.strip('voucher_payment_'))
                        if not voucher.recipient_msisdn:
                            description = "{voucher_code} - Guest".format(voucher_code=voucher.voucher_code)
                        else:
                            description = "{voucher_code} - {recipient_msisdn}"\
                                .format(voucher_code=voucher.voucher_code,
                                        recipient_msisdn=voucher.recipient_msisdn)
                    transactions_string += "{id}.{tag}R{amount} - {description}\n"\
                        .format(id=transactions_tracker,
                                tag=credit_tag,
                                amount=transaction.amount,
                                description=description)
                response = transactions_string
            else:
                response = "You have no transactions."
            return HttpResponse(response)


        if node_name == "Balance":
            logger.info(msisdn)
            profile = UserProfile.objects.get(user__username=msisdn)
            pocket = profile.default_pocket #profile.pockets.filter(active=True).order_by('created')[int(request.GET.get("ussd_response_Active_Pocket_"+node_name,profile.default_pocket))-1]
            response = "(((C) {tag}\n\n" \
                       "Balance: {balance} Crowdcoins".format(balance=pocket.balance(),tag=pocket.tag)
            return HttpResponse(response)


        if node_name == "Redeem_Voucher":
            profile = UserProfile.objects.get(user__username=msisdn)
            pocket_to = pocket = profile.default_pocket
            voucher_code = request.GET.get("ussd_response_Voucher_Code")
            if VoucherPaymentLead.objects.filter(active=True,voucher_code=voucher_code):
                voucher = VoucherPaymentLead.objects.get(active=True,voucher_code=voucher_code)
                if voucher.status in ["Pending","Awaiting Collection"]:
                    voucher.pocket_to = pocket_to
                    voucher.active = False
                    voucher.status = "Collected"
                    voucher.save()
                    response = "Thank you!\n{amount} Crowdcoin credited to {tag}.".format(amount=voucher.amount,tag=voucher.pocket_to.tag)

                    #Send redeemption sms
                    msg = "Hi {full_names}\n" \
                          "{pocket_name} has been credited with {amount} Crowdcoins.\nBalance:{balance} ".format(pocket_name=pocket_to.tag,
                                                                                             amount=voucher.amount,
                                                                                             full_names=profile.user.get_short_name(),
                                                                                             balance=pocket_to.balance())
                    send_sms(msg,profile.msisdn)

                else:

                    response = "You have entered an incorrect Voucher Security Pin."
            else:
                if VoucherPaymentLead.objects.filter(active=False, voucher_code=voucher_code):
                    if VoucherPaymentLead.objects.get(active=False,
                                                      voucher_code=voucher_code).pocket_to in profile.pockets.all():
                        response = "You have already redeemed this voucher"
                    else:
                        response = "The provided Voucher has already been redeemed"
                else:
                    response = "You have entered an incorrect Voucher number."
            return HttpResponse(response)

        if node_name == "Generate_Voucher":
            profile = UserProfile.objects.get(user__username=msisdn)
            pocket_from = profile.default_pocket
            amount = float(request.GET.get("ussd_response_Voucher_Amount"))
            if pocket_from.balance() >= amount and amount >= 0 :
                voucher = VoucherPaymentLead.objects.create(active=True,
                                                            pocket_from=pocket_from,
                                                            amount=amount,
                                                            sender_msisdn=msisdn,
                                                            recipient_msisdn=msisdn,
                                                            status='Awaiting Collection'
                                                            )


            else:
                if amount>0:
                    response = "Insufficient balance.\nAvailable Balance: {balance} (((c)".format(balance=pocket_from.balance())
                else:
                    response = "You entered an incorrect amount."

            return HttpResponse(response)

        else:
            response = "No option selected"
            return HttpResponse(response, status=200)

    except Exception as e:
        logger.exception(e)
        response="An error occurred. Please contact support\n" \
                 "0) Menu"
        return HttpResponse(response)


def create_funds_transaction_api(request):
    user_profile = UserProfile.objects.get(user__username=request.GET.get('username'),user__api_key__key=request.GET.get('api_key'))
    amount = float(request.GET.get('amount'))
    transaction_type = TransactionType.objects.get(name=request.GET.get('transaction_type'))
    payee = (request.GET.get('payee'))
    payee_profile = None
    reference = (request.GET.get("reference"))
    recipient_type = request.GET.get('recipient_type')
    if request.GET.get("on_hold"):
        on_hold=True
    else:
        on_hold=False
    if payee == "":
        payee=user_profile.user.username
    #calculate final amount
    if transaction_type.fee_type == "Amount":
        total_amount = amount + transaction_type.fee
    else:
        total_amount = math.ceil((amount*transaction_type.fee/100)+amount)
    if total_amount <= user_profile.balance:
        debit_trans = FundsTransaction.objects.create(
            profile=user_profile,
            amount=amount,
            transaction_type=transaction_type,
            description='%s : %s'%(payee,reference),
            status='Approved',
            on_hold=on_hold
        )
    else:
        response = {"status":"FAILED","response":"Insufficient funds"}
        return JsonResponse(response,safe=False)



def api_login(request):
    REQUIRED_FIELDS = ["username"]
    for field in REQUIRED_FIELDS:
        if field not in request.GET:
            response = {"status":"error","message":"Must provide {missing_key} when logging in.".format(missing_key=field)}
            return JsonResponse(response,safe=False)

    username = (request.GET["username"]).strip("'")
    password = (request.GET["password"]).strip("'")
    logger.info("%s %s"%(username,password))

    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            api_key = user.api_key.key
            response = {"status":"success","message":"Login successful","results":api_key}
        else:
            response = {"status":"failed","message":"Account disabled"}
    else:
        response = {"status":"success","message":"No matching account found"}
    return JsonResponse(response,safe=False)

def api_generate_deposit_lead(request):
  try:
    logger.info(request.GET)
    amount = request.GET.get('amount')
    network = Network.objects.get(name=request.GET.get('network'))
    simcards=SimCard.objects.filter(network=network,balance_day__lt=(network.daily_limit-float(amount)),status='Receiving')
    if len(simcards)>0:
        deposit_sim=simcards[0]
        deposit_sim.status = 'Paused'
        deposit_sim.save()
        transfer_number=deposit_sim.msisdn
        response = {"status":"success","response":{'amount':amount,'msisdn':transfer_number,'instructions':deposit_sim.network.airtime_transfer_instructions}}
    else:
        response = {"status":"error",'response':"WE COULD NOT ALLOCATE A RECIEVING NUMBER. TRY AGAIN WITH A LESSER AMOUNT OR TRY AGAIN TOMORROW."}

  except Exception as e:
    logger.warning(e.message)
    response = e.message
  return JsonResponse(response,safe=False)

def reset_password(request):
    username = request.GET.get('username')
    if username in ('',None):
        response = {"status":"FAILED","response":"Username not provided"}
        return JsonResponse(response,safe=False)
    if User.objects.filter(username=username).exists():
        user = User.objects.get(username=username)
        password = get_random_string(length=5,allowed_chars='1234567890abcderghijklmnopqrstuvwxyz')
        user.set_password(password)
        user.save()
        message = "Crowdcoin security alert.\nNew password:%s\nDidn't request this? Call us on +27213001793"% password
        send_sms(message,username)
        response = {"status":"SUCCESS","response":"A new password has been sent to %s" % username}
        return JsonResponse(response,safe=False)
    else:
        response = {"status":"FAILED","response":"No matching profile found"}
        return JsonResponse(response,safe=False)



@login_required
def export_funds_csv(request):
    try:
        # Create the HttpResponse object with the appropriate CSV header.
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="crowdcoin_%s.csv"' % request.user.username
        transactions_list = FundsTransaction.objects.filter(profile__user=request.user).order_by('-datetime')
        writer = csv.writer(response)
        writer.writerow(['ID', 'STAMP', 'DESCRIPTION', 'TYPE','AMOUNT','FEE'])
        for transaction in transactions_list:
            writer.writerow([transaction.id,transaction.datetime,transaction.description,transaction.transaction_type.action,transaction.amount,transaction.fee])

    except Exception,e:
        logger.warning(e)
    return response

def SmsInboundView(request):
    msisdn = request.GET.get('msisdn')
    sender = request.GET.get('sender')
    message = request.GET.get('message')
    msg_id = request.GET.get('msg_id')
    source_id = request.GET.get('source_id')
    network_id = request.GET.get('network_id')
    received_time = request.GET.get('received_time')

    try:
        inbox_msg=SmsInbound.objects.create(
            msisdn=msisdn,
            sender=(sender).strip('"'),
            message=message,
            msg_id=msg_id,
            source_id=source_id,
            network_id=network_id,
            received_time=received_time)

        message.split("")


    except Exception as e:
        logger.warning(e)
        return HttpResponse("Error")

    return  HttpResponse("Success")

@csrf_exempt
def api_merchant_registration(request):

#    thisisme_response=thisisme_id_check(identity_number=request.POST.get('identification_no'),
#        country_code=request.POST.get('identification_country'),
#        identity_type=request.POST.get('identification_type')
#    )
#    if not settings.DEBUG:
#        if thisisme_response.get('status') == 'error' :
#            return  JsonResponse(thisisme_response,safe=False) 
#        else:
#            thisisme_response = thisisme_response.get('response')
#            try:
#                i=(request.POST.get('last_name').upper()).index(thisisme_response.get('surname').upper())
#            except Exception as e:
#                logger.info(e.message)
#                response = {"status":"ERROR","response":"The provided identity information appears to be incorrect. Please check the supplied information and try again or contact support. "}
#                return JsonResponse(thisisme_response,safe=False) 

    if not User.objects.filter(username=request.POST.get('msisdn')).exists():
        user = User.objects.create(username=request.POST.get('msisdn'))
        user.set_password(request.POST.get('password'))

        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email','{username}@crowdcoin.co.za'.format(username=user.username))
        user.save()
        profile = UserProfile.objects.get_or_create(user=user)[0]
        profile.msisdn=request.POST.get('msisdn')
        profile.referrer=request.POST.get('referrer','ORGANIC')
        profile.display_name=request.POST.get('business_name')
        #profile.identification_type=request.POST.get('identification_type')
        #profile.identification_country=request.POST.get('identification_country')
        #profile.street_address = request.POST.get('street_address')
        #profile.suburb = request.POST.get('suburb')
        #profile.city = request.POST.get('city')
        #profile.gender = thisisme_response.get('gender')
        #profile.d_o_b = thisisme_response.get('date_of_birth')
        #profile.vital_status = thisisme_response.get('vital_status')   
        profile.is_verified=False
        profile.save()


        welcome_msg = "(((C) Hi {first_name}\n"\
            "Your Crowdcoin Merchant Details:\n"\
            "Username:{username}\n"\
            "Password:{password}\n"\
            "Send/Recieve Crowdcoins at http://dashboard.crowdcoin.co.za or dial *120*912*87*87#".format(first_name=user.first_name,username=user.username,password=request.POST.get('password'))

        bank_deposit_msg = "(((C) Please Top-up your Merchant account with at least R 350.\n\n"\
            "FNB Banking details:\n"\
            "Acc: 62634840319\n"\
            "Branch code: 250655\n"\
            "Refference: {username}".format(username=user.username) 

        send_sms(welcome_msg,profile.msisdn)
        #send_sms(bank_deposit_msg,profile.msisdn)

        try:
          description="Username: {username}\n First name: {first_name}\n Last name: {last_name}\n Mobile No.: {msisdn}\n Email: {email}\n Company: {business_name}\n Description: {business_description}\n Tel: {business_tel}\n Network: {network}\n".format(username=user.username, 
            first_name=user.first_name,
            last_name=user.last_name,
            email=profile.user.email,
            business_name=request.POST.get('business_name'),
            business_description=request.POST.get('business_description'),
            business_tel=request.POST.get('business_tel'),
            msisdn=profile.msisdn,
            network=profile.network)

          logger.info(description)

          freshdesk_new_ticket(
              name="{first_name} {last_name}".format(first_name=user.first_name,last_name=user.last_name),
              description=description,
              phone=profile.msisdn,
              email=profile.user.email,
              company=request.POST.get('business_name'),
              subject="NEW MERCHANT USER REGISTRATION"
          )
        except Exception as e:
            logger.warning(e.message)

        response = {"status":"SUCCESS","response":"Thank you for signing up. You can now sign in using your new username: {username}".format(username=user.username)}
    else:
        response = {"status":"ERROR","response":"Registration failed. A profile linked to {msisdn} already exists.".format(msisdn=request.POST.get('msisdn'))}  
    return JsonResponse(response,safe=False)

@csrf_exempt
def get_otp_view(request):
    if request.method == "POST":
        time_threshold = datetime.now() - timedelta(minutes=5)
        msisdn = request.POST.get('msisdn')
        if OneTimePin.objects.filter(address=msisdn,active=True,created__gt=time_threshold).exists():
            response = {"status": "error", "message": "OTP Verification Pending"}
        else:
            pin = random.randint(999, 9999)
            otp = OneTimePin.objects.create(address=msisdn,
                                            pin=pin,
                                            active=True)
            msg = "Crowdcoin OTP: {otp}".format(otp=otp.pin)
            send_sms(msg,msisdn)
            response = {"status":"success","message":"OTP sent to {msisdn}".format(msisdn=msisdn)}
    else:
        #Verify
        msisdn = request.GET.get('msisdn')
        otp = request.GET.get('otp')

        if OneTimePin.objects.filter(address=msisdn,pin=otp,active=True).exists():
            otp_obj = OneTimePin.objects.get(address=msisdn, pin=otp, active=True)
            otp_obj.active  = False
            otp_obj.save()

            response = {"status": "success", "message": "OTP Verified"}
        else:
            response = {"status": "error", "message": "OTP Verification failed"}
    return JsonResponse(response,safe=False)    