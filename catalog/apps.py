from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = 'catalog'

    def ready(self):
        # Invalidate the cached home page data whenever content it shows changes
        from django.core.cache import cache
        from django.db.models.signals import post_delete, post_save

        def _clear_home_cache(*args, **kwargs):
            cache.delete('home_page_data_v1')

        from core.models import HeroSlide, HomeCategoryCard
        from reviews.models import Review

        from .models import Brand, Product, ProductVariant

        for model in (Product, ProductVariant, Brand, HeroSlide, HomeCategoryCard, Review):
            post_save.connect(_clear_home_cache, sender=model, weak=False,
                              dispatch_uid=f'home-cache-{model.__name__}-save')
            post_delete.connect(_clear_home_cache, sender=model, weak=False,
                                dispatch_uid=f'home-cache-{model.__name__}-delete')
