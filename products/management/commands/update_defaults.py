from django.core.management.base import BaseCommand
from products.models import Price
from users.models import CustomUser

class Command(BaseCommand):
    help = 'Update default values for new fields'

    def handle(self, *args, **options):
        Price.objects.update(margen_prod=0.20, descuento_prod=0.0)
        CustomUser.objects.update(descuento_cliente=0.0)
        self.stdout.write(self.style.SUCCESS('Defaults updated successfully.')) 