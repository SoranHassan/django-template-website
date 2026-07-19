from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include

from core.views import robots_txt, NewsletterSubscribeView, StaticPageView
from .sitemaps import SITEMAPS

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('catalog.urls')),
    path('accounts/', include('accounts.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path(settings.DASHBOARD_URL, include('dashboard.urls')),
    path('reviews/', include('reviews.urls')),
    path('blog/', include('blog.urls')),
    path('api/v1/', include('api.urls')),
    path('ckeditor5/', include('django_ckeditor_5.urls')),

    # SEO
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('newsletter/subscribe/', NewsletterSubscribeView.as_view(), name='newsletter_subscribe'),

    # Editable content pages (terms, privacy, about...) - str slug allows Persian
    path('page/<str:slug>/', StaticPageView.as_view(), name='static_page'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error pages (403/404 branded like the site, 500 standalone)
handler403 = 'core.views.error_403'
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'