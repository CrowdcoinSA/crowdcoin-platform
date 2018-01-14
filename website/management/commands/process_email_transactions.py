from django.core.management.base import BaseCommand, CommandError
from website.utils import ProcessEmailTransaction,process_vodacom_leads

class Command(BaseCommand):

    def handle(self, *args, **options):
        #ProcessEmailTransaction()
        process_vodacom_leads()
