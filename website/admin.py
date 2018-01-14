from django.contrib import admin
from website.models import *
from website.tasks import create_transaction
import logging

logger = logging.getLogger(__name__)

# Register your models
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user',"network","identification_no","identification_country"]
    search_fields = ["user__username",'user__first_name','user__last_name']
    list_filter = ["user__date_joined","user__last_login","network"]
    raw_id_fields = ("user",)


class AirtimeDepositLeadAdmin(admin.ModelAdmin):
    def recieved_airtime(modeladmin, request, queryset):
        queryset.update(status="Accepted",updated=True)
        for obj in queryset:
            obj.save()

    recieved_airtime.short_description = "Mark selected leads as received"

    list_display = ['pocket', "amount", "status"]
    search_fields = ["msisdn","profile__user__username"]
    list_filter = ['created',"status", "sim_card__network"]
    actions = [recieved_airtime]


class CrowdcoinPaymentLeadAdmin(admin.ModelAdmin):
    def recieved_airtime(modeladmin, request, queryset):
        queryset.update(status="Accepted",updated=True)
        for obj in queryset:
            obj.save()

    recieved_airtime.short_description = "Mark selected leads as received"

    list_display = ["pocket_from", "pocket_to", "amount", "status"]
    search_fields = ["msisdn","identifiers__value"]
    list_filter = ['created',"status", "sim_card__network"]
    actions = [recieved_airtime]


class AirtimeDepositTransactionAdmin(admin.ModelAdmin):
    list_display = ["amount", "description","created","sim_card"]
    list_filter = ['created',"expiary_date","sim_card"]

class SimCardAdmin(admin.ModelAdmin):
    def make_receiving(modeladmin, request, queryset):
        queryset.update(status="Receiving")
        for obj in queryset:
            obj.save()

    make_receiving.short_description = "Mark selected sims as Receiving"

    def make_paused(modeladmin, request, queryset):
        queryset.update(status="Circulating")
        for obj in queryset:
            obj.save()

    make_paused.short_description = "Mark selected sims as Paused"

    def transfer_daily_balance(modeladmin, request, queryset):
        queryset.update(status="Deactivated")
        for obj in queryset:
            obj.balance_month += obj.balance_day
            obj.balance_day = 0
            obj.save()

    transfer_daily_balance.short_description = "Transfer day balance to month balance."

    list_display = ["sim_no","network","balance_day","balance_month","msisdn","status"]
    search_fields = ["msisdn","sim_no"]
    list_filter = ['network',"status","is_active"]
    actions = [make_receiving,make_paused,transfer_daily_balance]



admin.site.register(SmsOutBound)
admin.site.register(SmsInbound)
admin.site.register(UserProfile,UserProfileAdmin)
admin.site.register(Network)
admin.site.register(SimCard,SimCardAdmin)
admin.site.register(UniqueIdentifier)
admin.site.register(Pocket)
admin.site.register(Transaction)
admin.site.register(AirtimeDepositLead,AirtimeDepositLeadAdmin)
admin.site.register(CrowdcoinPaymentLead)
admin.site.register(BankPaymentLead)
admin.site.register(BankDepositLead)
admin.site.register(SmsTemplate)
admin.site.register(VoucherPaymentLead)
admin.site.register(Merchant)
admin.site.register(Promotion)
admin.site.register(ClaimedPromotion)
admin.site.register(OneTimePin)
admin.site.register(AirtimeDepositTransaction,AirtimeDepositTransactionAdmin)