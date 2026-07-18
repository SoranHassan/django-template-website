"""Shared helpers for the core app."""
import io
import os

from django.core.files.uploadedfile import InMemoryUploadedFile

# Above this size (bytes) or side (px) an uploaded raster image gets optimized
OPTIMIZE_THRESHOLD_BYTES = 300 * 1024
MAX_SIDE = 1920
JPEG_QUALITY = 82


def optimize_image(uploaded, max_side=MAX_SIDE, quality=JPEG_QUALITY, force=False):
    """Downscale/compress an uploaded raster image; returns the (possibly new) file.

    SVGs, GIFs and small files pass through untouched (unless force=True,
    which skips the byte-size shortcut so oversized-but-light images still
    get downscaled). Output is WebP (transparency preserved; ~30% smaller than JPEG). Never raises - on any problem the original upload is
    returned unchanged.
    """
    try:
        from PIL import Image

        name = getattr(uploaded, 'name', '') or ''
        ext = os.path.splitext(name)[1].lower()
        if ext in ('.svg', '.gif'):
            return uploaded
        if not force and uploaded.size < OPTIMIZE_THRESHOLD_BYTES:
            return uploaded

        uploaded.seek(0)
        img = Image.open(uploaded)
        img.load()

        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side), Image.LANCZOS)

        # WebP for everything (supports transparency, ~30% smaller than JPEG,
        # supported by all modern browsers)
        has_alpha = img.mode in ('RGBA', 'LA') or (
            img.mode == 'P' and 'transparency' in img.info)
        buf = io.BytesIO()
        if has_alpha:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            img.save(buf, format='WEBP', quality=quality, method=4)
        else:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(buf, format='WEBP', quality=quality, method=4)
        out_ext, ctype = '.webp', 'image/webp'

        # Keep the original when optimization would not actually shrink it
        # (unless we were forced to downscale oversized dimensions)
        if not force and buf.getbuffer().nbytes >= uploaded.size:
            uploaded.seek(0)
            return uploaded

        new_name = os.path.splitext(os.path.basename(name))[0] + out_ext
        buf.seek(0)
        return InMemoryUploadedFile(buf, None, new_name, ctype,
                                    buf.getbuffer().nbytes, None)
    except Exception:
        try:
            uploaded.seek(0)
        except Exception:
            pass
        return uploaded


def runtime_config(field, env_setting):
    """DB-first runtime config: SiteSetting.<field> when set, else settings.<env_setting>.

    DB changes apply instantly (no restart); .env changes still need a restart.
    Never raises - falls back to the env value before migrations exist.
    """
    from django.conf import settings as dj_settings

    env_value = getattr(dj_settings, env_setting, '')
    try:
        from .models import SiteSetting
        db_value = getattr(SiteSetting.get(), field, '') or ''
        return db_value.strip() or env_value
    except Exception:
        return env_value


def feature_enabled(flag):
    """True when the given SiteSetting feature flag (e.g. 'feature_blog') is on.
    Fails open so a missing table (pre-migrate) never breaks a page."""
    from core.models import SiteSetting
    try:
        return bool(getattr(SiteSetting.get(), flag, True))
    except Exception:
        return True
