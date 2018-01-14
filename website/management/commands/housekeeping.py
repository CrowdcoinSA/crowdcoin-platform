from django.core.management.base import BaseCommand, CommandError
from website.utils import email_admin_summary

class Command(BaseCommand):

    def handle(self, *args, **options):
        email_admin_summary()
