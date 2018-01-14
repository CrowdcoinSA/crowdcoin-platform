from django.core.management.base import BaseCommand, CommandError
from website.utils import populate_plans_limits

class Command(BaseCommand):

    def handle(self, *args, **options):
        populate_plans_limits()
