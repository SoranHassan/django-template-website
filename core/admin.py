from django.contrib import admin
from .models import Announcement

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('text', 'link_text', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    search_fields = ('text',)

from .models import HeroSlide


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title',)


from .models import SiteSetting, HomeCategoryCard


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'home_watermark', 'topbar_style')

    def has_add_permission(self, request):
        # فقط یک ردیف تنظیمات — اگر وجود ندارد اجازه ساخت بده
        return not SiteSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HomeCategoryCard)
class HomeCategoryCardAdmin(admin.ModelAdmin):
    list_display = ('title', 'link', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('title',)


from .models import NewsletterSubscriber, NewsletterCampaign


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('email',)


@admin.register(NewsletterCampaign)
class NewsletterCampaignAdmin(admin.ModelAdmin):
    list_display = ('subject', 'recipients_count', 'sent_at')
    search_fields = ('subject',)
    readonly_fields = ('sent_at', 'recipients_count')
