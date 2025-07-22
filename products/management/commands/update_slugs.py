from django.core.management.base import BaseCommand
from products.models import Product, Category, Brand

class Command(BaseCommand):
    help = "Genera o actualiza los slugs de todos los productos según la lógica actual."

    def handle(self, *args, **options):
        updated = 0
        # Update Products
        for product in Product.objects.all():
            new_slug = product._generate_slug()
            if product.slug != new_slug:
                product.slug = new_slug
                product.save(update_fields=["slug"])
                updated += 1
        # Update Categories
        for cat in Category.objects.all():
            cat.save()
        # Update Brands
        for brand in Brand.objects.all():
            brand.save()
        self.stdout.write(self.style.SUCCESS(f"Slugs actualizados: {updated}")) 