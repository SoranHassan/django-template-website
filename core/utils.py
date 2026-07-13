"""Shared helpers for the core app."""
import io
import os

from django.core.files.uploadedfile import InMemoryUploadedFile

# Above this size (bytes) or side (px) an uploaded raster image gets optimized
OPTIMIZE_THRESHOLD_BYTES = 300 * 1024
MAX_SIDE = 1920
JPEG_QUALITY = 82


def optimize_image(uploaded, max_side=MAX_SIDE, quality=JPEG_QUALITY):
    """Downscale/compress an uploaded raster image; returns the (possibly new) file.

    SVGs, GIFs and small files pass through untouched. PNGs with transparency
    stay PNG; everything else becomes an optimized JPEG. Never raises - on any
    problem the original upload is returned unchanged.
    """
    try:
        from PIL import Image

        name = getattr(uploaded, 'name', '') or ''
        ext = os.path.splitext(name)[1].lower()
        if ext in ('.svg', '.gif', '.webp'):
            return uploaded
        if uploaded.size < OPTIMIZE_THRESHOLD_BYTES:
            return uploaded

        uploaded.seek(0)
        img = Image.open(uploaded)
        img.load()

        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side), Image.LANCZOS)

        has_alpha = img.mode in ('RGBA', 'LA') or (
            img.mode == 'P' and 'transparency' in img.info)
        buf = io.BytesIO()
        if has_alpha:
            img.save(buf, format='PNG', optimize=True)
            out_ext, ctype = '.png', 'image/png'
        else:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(buf, format='JPEG', quality=quality, optimize=True, progressive=True)
            out_ext, ctype = '.jpg', 'image/jpeg'

        # Keep the original when optimization would not actually shrink it
        if buf.getbuffer().nbytes >= uploaded.size:
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
