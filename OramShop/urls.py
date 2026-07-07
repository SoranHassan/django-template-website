from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('catalog.urls')),
    path('accounts/', include('accounts.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('reviews/', include('reviews.urls')),
    path('404/', include('core.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# هندلر ۴۰۴ سفارشی
handler404 = 'core.views.error_404'