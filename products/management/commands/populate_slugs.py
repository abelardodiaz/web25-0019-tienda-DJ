from django.core.management.base import BaseCommand
from products.models import Category, Brand
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Genera slugs para categorías y marcas existentes'
    
    def handle(self, *args, **kwargs):
        # Para categorías
        for categoria in Category.objects.filter(slug__isnull=True):
            categoria.slug = slugify(categoria.name)
            categoria.save()
            self.stdout.write(f'Slug generado para categoría: {categoria.name} -> {categoria.slug}')
        
        # Para marcas
        for marca in Brand.objects.filter(slug__isnull=True):
            marca.slug = slugify(marca.name)
            marca.save()
            self.stdout.write(f'Slug generado para marca: {marca.name} -> {marca.slug}')
        
        self.stdout.write(self.style.SUCCESS('¡Slugs generados exitosamente!')) 