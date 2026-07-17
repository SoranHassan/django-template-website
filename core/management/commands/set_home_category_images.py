"""Wire the images the admin dropped into media/banners to the 4 home category cards.

Usage:
    python manage.py set_home_category_images                # auto: first 4 images by name
    python manage.py set_home_category_images --dir banners  # custom folder inside media/
    python manage.py set_home_category_images --dry-run      # only report sizes, change nothing

For each image the command reports its dimensions and file size; anything larger
than 1200px or 300KB is downscaled/recompressed (originals stay untouched - the
optimized copy is saved through the ImageField). Images are assigned, in
filename order, to the four main clothing cards (تیشرت، هودی و سویشرت،
شلوار، کفش) - cards are created when missing and linked to the real category
slug when one exists.
"""
import os

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.webp')

# Filename hints -> card definition (title, subtitle, link builder)
# Recognized names like mens.jpg / womens.jpg / childrens.jpg / accessories.jpg
# NOTE: 'women' must be checked BEFORE 'men' ('men' is a substring of 'womens')
NAME_HINTS = [
    (('women', 'woman', 'zanane', 'ladies'), ('زنانه', 'پوشاک بانوان', '/shop/?gender=women', [])),
    (('men', 'man', 'mardane'), ('مردانه', 'پوشاک آقایان', '/shop/?gender=men', [])),
    (('child', 'kid', 'bache'), ('بچگانه', 'پوشاک کودکان', '/shop/?gender=kids', [])),
    (('access', 'aksesor'), ('اکسسوری', 'کیف، کلاه و مکمل استایل', '', ['اکسسوری', 'اکسسوری‌ها'])),
    (('tshirt', 'tishert', 'shirt'), ('تیشرت', 'خنک و راحت', '', ['تیشرت', 'تی‌شرت', 'تی شرت'])),
    (('hood', 'sweat'), ('هودی و سویشرت', 'گرم و اسپرت', '', ['هودی و سویشرت', 'هودی', 'سویشرت'])),
    (('pant', 'shalvar', 'jean'), ('شلوار', 'جین و کتان', '', ['شلوار'])),
    (('shoe', 'kafsh', 'sneaker'), ('کفش', 'اسپرت و رسمی', '', ['کفش'])),
]

# Fallback when no filename matches any hint: first four images by name
CARD_SPECS = [
    ('تیشرت', 'خنک و راحت', ['تیشرت', 'تی‌شرت', 'تی شرت']),
    ('هودی و سویشرت', 'گرم و اسپرت', ['هودی و سویشرت', 'هودی', 'سویشرت']),
    ('شلوار', 'جین و کتان', ['شلوار']),
    ('کفش', 'اسپرت و رسمی', ['کفش']),
]


def match_hint(filename):
    """Return the card spec matching this filename, or None."""
    stem = os.path.splitext(filename)[0].lower()
    for keys, spec in NAME_HINTS:
        if any(k in stem for k in keys):
            return spec
    return None


class Command(BaseCommand):
    help = 'Assign media/banners images to the 4 home category cards (with size check + optimization)'

    def add_arguments(self, parser):
        parser.add_argument('--dir', default='banners',
                            help='Folder inside MEDIA_ROOT to read images from (default: banners)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Only report image sizes; change nothing')

    def handle(self, *args, **opts):
        from PIL import Image

        from catalog.models import Category
        from core.models import HomeCategoryCard
        from core.utils import optimize_image

        folder = os.path.join(settings.MEDIA_ROOT, opts['dir'])
        if not os.path.isdir(folder):
            self.stderr.write(self.style.ERROR(f'پوشه پیدا نشد: {folder}'))
            return

        images = sorted(
            f for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS)
        if not images:
            self.stderr.write(self.style.ERROR(f'هیچ عکسی در {folder} نیست'))
            return

        self.stdout.write(f'\n{len(images)} عکس پیدا شد در {opts["dir"]}/ :\n')
        report = []
        for name in images:
            path = os.path.join(folder, name)
            size_kb = os.path.getsize(path) // 1024
            with Image.open(path) as im:
                w, h = im.size
            big = max(w, h) > 1200 or size_kb > 300
            report.append((name, w, h, size_kb, big))
            flag = 'بزرگ است → بهینه می‌شود' if big else 'مناسب است'
            self.stdout.write(f'  • {name}: {w}x{h}px , {size_kb}KB — {flag}')

        if opts['dry_run']:
            self.stdout.write(self.style.WARNING('\n--dry-run: تغییری اعمال نشد'))
            return

        # Prefer filename hints (mens/womens/childrens/accessories/...);
        # unrecognized files are skipped so a stray image never lands on a card.
        assignments = []
        hinted = [(name, match_hint(name)) for name in images]
        if any(spec for _, spec in hinted):
            skipped = []
            for name, spec in hinted:
                if spec:
                    assignments.append((name, spec))
                else:
                    skipped.append(name)
            for name in skipped:
                self.stdout.write(self.style.WARNING(
                    f'  ! {name}: از روی نام قابل تشخیص نیست — رد شد'))
        else:
            for (title, subtitle, cat_names), name in zip(CARD_SPECS, images):
                assignments.append((name, (title, subtitle, '', cat_names)))

        if len(assignments) < 4:
            self.stdout.write(self.style.WARNING(
                f'\n{len(assignments)} کارت به‌روزرسانی می‌شود'))

        self.stdout.write('')
        for order, (name, (title, subtitle, fixed_link, cat_names)) in enumerate(assignments):
            link = fixed_link
            if not link:
                cat = Category.objects.filter(name__in=cat_names, is_active=True).first()
                link = f'/shop/?category={cat.slug}' if cat else '/shop/'
            card, _ = HomeCategoryCard.objects.get_or_create(
                title=title, defaults={'subtitle': subtitle, 'link': link,
                                       'order': order, 'is_active': True})
            card.link = link
            card.subtitle = card.subtitle or subtitle
            card.order = order
            card.is_active = True
            path = os.path.join(folder, name)
            with open(path, 'rb') as fh:
                uploaded = File(fh, name=name)
                uploaded.size = os.path.getsize(path)
                big = max(Image.open(path).size) > 1200 or uploaded.size > 300 * 1024
                optimized = optimize_image(uploaded, max_side=1200, force=big)
                # use the optimizer's name so the .webp extension matches the content
                card.image.save(getattr(optimized, 'name', name) or name, optimized, save=False)
            card.save()
            self.stdout.write(self.style.SUCCESS(f'  ✓ {name} ← کارت «{title}» ({link})'))

        self.stdout.write(self.style.SUCCESS(
            '\nتمام شد — کارت‌های صفحه اصلی حالا از این عکس‌ها استفاده می‌کنند.\n'
            'نگاشت از روی نام فایل انجام شد؛ اگر چیزی جابه‌جا بود،\n'
            'از پنل ← «کارت‌های صفحه اصلی» عکس هر کارت را عوض کنید.'))
