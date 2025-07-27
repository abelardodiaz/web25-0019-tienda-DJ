from django.core.management.base import BaseCommand
from products.models import Category, Brand
from django.utils.text import slugify
import itertools

class Command(BaseCommand):
    help = 'Update slugs for existing Categories and Brands'

    def handle(self, *args, **kwargs):
        # Update Categories
        for cat in Category.objects.all():
            if not cat.slug:
                base_slug = slugify(cat.name)
                unique_slug = base_slug
                for i in itertools.count(1):
                    if not Category.objects.filter(slug=unique_slug).exclude(id=cat.id).exists():
                        break
                    unique_slug = f"{base_slug}-{i}"
                cat.slug = unique_slug
            cat.save()
                self.stdout.write(self.style.SUCCESS(f'Updated slug for category: {cat.name} -> {cat.slug}'))
        
        # Update Brands
        for brand in Brand.objects.all():
            if not brand.slug:
                base_slug = slugify(brand.name)
                unique_slug = base_slug
                for i in itertools.count(1):
                    if not Brand.objects.filter(slug=unique_slug).exclude(id=brand.id).exists():
                        break
                    unique_slug = f"{base_slug}-{i}"
                brand.slug = unique_slug
            brand.save()
                self.stdout.write(self.style.SUCCESS(f'Updated slug for brand: {brand.name} -> {brand.slug}'))
        
        self.stdout.write(self.style.SUCCESS('Successfully updated all slugs!')) 