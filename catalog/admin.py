from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Brand, Category, Size, Color,
    Product, ProductImage, ProductVariant, SizeChart)




@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'is_main', 'order', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="60" '
                'style="border-radius:8px; object-fit:cover;">',obj.image.url)
        return '-'
    image_preview.short_description = 'پیش‌ نمایش'


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('size', 'color', 'stock', 'price', 'color_preview')
    readonly_fields = ('color_preview',)

    def color_preview(self, obj):
        if obj.color:
            return format_html(
                '<div style="width:24px; height:24px; border-radius:50%; '
                'background:{}; border:1px solid #ddd;"></div>',obj.color.hex_code)
        return '-'
    color_preview.short_description = 'رنگ'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_main', 'order')
    list_filter = ('is_main',)
    search_fields = ('product__name',)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product','size','color','stock','price','is_available')
    list_filter = ('size', 'color')
    search_fields = ('product__name',)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_preview', 'hex_code')
    search_fields = ('name',)

    def color_preview(self, obj):
        return format_html(
            '<div style="width:30px; height:30px; border-radius:50%; '
            'background:{}; border:2px solid #ddd; display:inline-block;"></div>',obj.hex_code)
    color_preview.short_description = 'رنگ'

    class Media:
        css = {'all': ('https://cdnjs.cloudflare.com/ajax/libs/spectrum/1.8.1/spectrum.min.css',)}
        js = ('https://cdnjs.cloudflare.com/ajax/libs/spectrum/1.8.1/spectrum.min.js',)

    def changeform_view(self, request, *args, **kwargs):
        # inject color picker JS
        extra = '''
        <script>
        window.addEventListener('load', function() {
            const hexInput = document.querySelector('[name="hex_code"]');
            if (hexInput && typeof $.fn.spectrum !== 'undefined') {
                $(hexInput).spectrum({
                    type: "color",
                    showInput: true,
                    showInitial: true,
                    preferredFormat: "hex",
                    change: function(color) {
                        hexInput.value = color.toHexString();
                    }
                });
            }
        });
        </script>
        '''
        response = super().changeform_view(request, *args, **kwargs)
        if hasattr(response, 'context_data'):
            response.context_data['adminform'].form.fields['hex_code'].help_text = (
                'روی فیلد کلیک کنید تا انتخابگر رنگ باز شود')
        return response



class SizeChartInline(admin.TabularInline):
    model = SizeChart
    extra = 1
    fields = ('size', 'shoulder', 'sleeve', 'chest', 'length_top', 'waist', 'hip', 'crotch', 'length_bottom')
    verbose_name = 'سایزبندی'
    verbose_name_plural = 'جدول سایزبندی'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'brand', 'category','category_type', 'gender', 'price','is_active', 'created_at')
    list_filter = ('is_active', 'gender', 'category_type', 'brand', 'category')
    search_fields = ('name', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-created_at',)
    inlines = (ProductImageInline, ProductVariantInline, SizeChartInline)

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('sku', 'name', 'slug', 'brand', 'category', 'gender', 'category_type', 'description')
        }),
        ('قیمت', {
            'fields': ('price', 'original_price')
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        }),
    )