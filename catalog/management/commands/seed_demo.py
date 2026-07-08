"""
داده نمونه فروشگاه:  python manage.py seed_demo
۲۴+ محصول با تصویر، ۸ دسته‌بندی، ۸ برند با لوگو، روش‌های ارسال، کوپن، اسلاید بنر و نظرات
"""
import io
import random

from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from PIL import Image, ImageDraw, ImageFont

from accounts.models import CustomUser
from catalog.models import Brand, Category, Color, Product, ProductImage, ProductVariant, Size
from core.models import Announcement, HeroSlide
from orders.models import Coupon, ShippingMethod
from reviews.models import Review

PALETTE = ['#1A1A1A', '#264653', '#2a9d8f', '#6d597a', '#457b9d', '#606c38',
           '#9a8c98', '#4a4e69', '#22333b', '#3a5a40', '#5e548e', '#355070']


def product_image(color_hex, label=''):
    img = Image.new('RGB', (600, 800), color_hex)
    draw = ImageDraw.Draw(img)
    base = img.getpixel((0, 0))
    light = tuple(min(255, c + 26) for c in base)
    dark = tuple(max(0, c - 18) for c in base)
    draw.rectangle([50, 70, 550, 640], fill=light)
    draw.rectangle([50, 660, 550, 730], fill=dark)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=82)
    return ContentFile(buf.getvalue())


def brand_logo(name):
    img = Image.new('RGB', (360, 140), '#ffffff')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 52)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), name, font=font)
    x = (360 - (bbox[2] - bbox[0])) / 2
    y = (140 - (bbox[3] - bbox[1])) / 2 - bbox[1]
    draw.text((x, y), name, fill='#1A1A1A', font=font)
    draw.line([(x, y + 74), (x + bbox[2] - bbox[0], y + 74)], fill='#00E6FF', width=6)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return ContentFile(buf.getvalue())


def hero_image(color_hex, index):
    img = Image.new('RGB', (1600, 640), color_hex)
    draw = ImageDraw.Draw(img)
    for i in range(6):
        x = 150 + i * 240
        shade = tuple(min(255, c + 14 + i * 4) for c in img.getpixel((0, 0)))
        draw.ellipse([x, 120 + (i % 3) * 60, x + 190, 310 + (i % 3) * 60], fill=shade)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=80)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = 'ایجاد داده نمونه فروشگاه (محصول، برند، دسته، ارسال، کوپن، بنر)'

    def handle(self, *args, **options):
        random.seed(1404)

        # ---------- روش‌های ارسال ایرانی ----------
        for order_i, (name, price, desc) in enumerate([
            ('پست پیشتاز', 65000, 'تحویل ۲ تا ۴ روز کاری'),
            ('پست سفارشی', 45000, 'تحویل ۴ تا ۷ روز کاری'),
            ('تیپاکس', 95000, 'تحویل ۱ تا ۳ روز کاری — پرداخت در محل باربری'),
            ('پیک موتوری (تهران)', 80000, 'تحویل همان روز — فقط تهران'),
        ]):
            ShippingMethod.objects.get_or_create(
                name=name, defaults={'price': price, 'description': desc, 'order': order_i})
        self.stdout.write('✓ روش‌های ارسال')

        # ---------- برندها (لوگودار) ----------
        brand_names = ['Nike', 'Adidas', 'Zara', 'H&M', 'Puma', 'Mango', 'Bershka', 'LC Waikiki']
        brands = []
        for name in brand_names:
            brand, created = Brand.objects.get_or_create(
                name=name, defaults={'slug': name.lower().replace(' ', '-').replace('&', 'and')})
            if created or not brand.logo:
                brand.logo.save(f'{brand.slug}.png', brand_logo(name), save=True)
            brands.append(brand)
        self.stdout.write('✓ برندها')

        # ---------- دسته‌بندی‌ها ----------
        cat_defs = ['تیشرت', 'پیراهن', 'شلوار', 'هودی و سویشرت', 'کفش', 'کاپشن و پالتو', 'اکسسوری', 'ست ورزشی']
        categories = []
        for i, name in enumerate(cat_defs):
            cat, _ = Category.objects.get_or_create(name=name, defaults={'slug': f'cat-{i + 1}'})
            categories.append(cat)
        self.stdout.write('✓ دسته‌بندی‌ها')

        # ---------- سایز و رنگ ----------
        sizes = [Size.objects.get_or_create(name=s)[0] for s in ['S', 'M', 'L', 'XL', 'XXL']]
        colors = [Color.objects.get_or_create(name=n, defaults={'hex_code': h})[0] for n, h in [
            ('مشکی', '#212121'), ('سفید', '#fafafa'), ('سرمه‌ای', '#1d3557'),
            ('طوسی', '#8d99ae'), ('زیتونی', '#606c38'), ('قرمز', '#e63946')]]

        # ---------- محصولات ----------
        product_defs = [
            ('تیشرت نخی یقه گرد', 0, 'men'), ('تیشرت اورسایز طرح‌دار', 0, 'men'),
            ('تیشرت بیسیک زنانه', 0, 'women'), ('کراپ تیشرت زنانه', 0, 'women'),
            ('پیراهن مردانه کلاسیک', 1, 'men'), ('پیراهن چهارخانه', 1, 'men'),
            ('شومیز زنانه حریر', 1, 'women'), ('پیراهن جین زنانه', 1, 'women'),
            ('شلوار جین راسته', 2, 'men'), ('شلوار کتان مردانه', 2, 'men'),
            ('شلوار جین مام‌استایل', 2, 'women'), ('شلوار پارچه‌ای زنانه', 2, 'women'),
            ('هودی اورسایز', 3, 'unisex'), ('سویشرت زیپ‌دار', 3, 'men'),
            ('هودی کلاه‌دار زنانه', 3, 'women'), ('دورس یقه گرد', 3, 'unisex'),
            ('کفش اسپرت روزمره', 4, 'men'), ('کفش رانینگ حرفه‌ای', 4, 'unisex'),
            ('کتانی زنانه سفید', 4, 'women'), ('نیم‌بوت چرم مردانه', 4, 'men'),
            ('کاپشن پافر', 5, 'men'), ('پالتو بلند زنانه', 5, 'women'),
            ('بارانی زنانه', 5, 'women'), ('ژاکت بافت مردانه', 5, 'men'),
            ('کلاه بیسبال', 6, 'unisex'), ('کیف دوشی چرم', 6, 'women'),
            ('کمربند چرم مردانه', 6, 'men'), ('شال گردن بافت', 6, 'unisex'),
            ('ست تیشرت و شلوار ورزشی', 7, 'men'), ('لگ ورزشی زنانه', 7, 'women'),
        ]

        created_count = 0
        for i, (name, cat_i, gender) in enumerate(product_defs):
            slug = f'product-seed-{i + 1}'
            if Product.objects.filter(slug=slug).exists():
                continue
            price = random.choice([290, 390, 490, 590, 690, 790, 890, 990, 1190, 1490, 1890, 2490]) * 1000
            original = int(price * random.choice([1.2, 1.3, 1.45])) if i % 3 != 2 else None
            product = Product.objects.create(
                name=name, slug=slug, brand=brands[i % len(brands)], category=categories[cat_i],
                gender=gender, price=price, original_price=original, sku=f'OS-{1400 + i}',
                description=(f'{name} از جنس درجه یک با دوخت تمیز و ماندگاری بالا. '
                             'مناسب استفاده روزمره؛ قبل از خرید جدول سایزبندی را ببینید.'))

            for j in range(3):
                pi = ProductImage(product=product, is_main=(j == 0), order=j)
                pi.image.save(f'{slug}-{j}.jpg',
                              product_image(PALETTE[(i + j) % len(PALETTE)]), save=True)

            for size in random.sample(sizes, k=3):
                for color in random.sample(colors, k=2):
                    ProductVariant.objects.create(product=product, size=size, color=color,
                                                  stock=random.randint(0, 15))
            created_count += 1
        self.stdout.write(f'✓ {created_count} محصول')

        # ---------- بنرهای هیرو ----------
        if not HeroSlide.objects.exists():
            slides = [
                ('کالکشن جدید بهار', 'جدیدترین مدل‌های پوشاک مردانه و زنانه', '#16324f'),
                ('تا ۴۰٪ تخفیف پوشاک زنانه', 'فرصت محدود — همین حالا خرید کنید', '#1A1A1A'),
                ('ارسال رایگان خرید بالای ۱ میلیون', 'به سراسر ایران با پست پیشتاز', '#22333b'),
            ]
            for i, (title, subtitle, color_hex) in enumerate(slides):
                slide = HeroSlide(title=title, subtitle=subtitle, order=i)
                slide.image.save(f'hero-{i + 1}.jpg', hero_image(color_hex, i), save=True)
        self.stdout.write('✓ اسلایدهای بنر')

        # ---------- کوپن و اطلاعیه ----------
        now = timezone.now()
        Coupon.objects.get_or_create(code='WELCOME10', defaults=dict(
            discount_type='percent', discount_value=10, max_discount_amount=200000,
            valid_from=now, valid_until=now + timedelta(days=90), max_uses=0, max_uses_per_user=1))
        Coupon.objects.get_or_create(code='ORAM50', defaults=dict(
            discount_type='fixed', discount_value=50000, min_order_amount=500000,
            valid_from=now, valid_until=now + timedelta(days=30)))
        Announcement.objects.get_or_create(
            text='ارسال رایگان برای خرید بالای ۱ میلیون تومان 🚚',
            defaults={'link': '/shop/', 'link_text': 'خرید کنید'})
        self.stdout.write('✓ کوپن و اطلاعیه')

        # ---------- نظرات نمونه ----------
        reviewer, created = CustomUser.objects.get_or_create(
            mobile='09120000010', defaults={'first_name': 'مشتری', 'last_name': 'نمونه'})
        if created:
            reviewer.password = make_password('sample12345')
            reviewer.save()
        bodies = ['کیفیت عالی بود، ممنون از اُرام‌شاپ.', 'سایزبندی دقیق بود و به موقع رسید.',
                  'جنس پارچه خوبه، پیشنهاد می‌کنم.', 'نسبت به قیمتش فوق‌العاده‌ست.']
        for product in Product.objects.filter(slug__startswith='product-seed-')[:12]:
            Review.objects.get_or_create(product=product, user=reviewer, defaults=dict(
                rating=random.randint(4, 5), title='راضی بودم',
                body=random.choice(bodies), is_approved=True))
        self.stdout.write('✓ نظرات')

        self.stdout.write(self.style.SUCCESS('داده نمونه کامل شد ✅'))
