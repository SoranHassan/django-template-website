# 🔌 راهنمای اتصال به API فروشگاه OramShop

این سند نحوهٔ اتصال به **API نسخهٔ ۱** فروشگاه را توضیح می‌دهد. این API برای ربات
تلگرام، اپ موبایل، یا هر سرویس بیرونی طراحی شده و با **Django REST Framework** و
ویوهای کلاس‌محور نوشته شده است.

---

## ۱. مبانی

| مورد | مقدار |
|------|-------|
| آدرس پایه (Base URL) | `https://oramshop.ir/api/v1/` |
| قالب پاسخ | JSON (فقط) |
| متد مجاز | فقط `GET` (متدهای دیگر → خطای ۴۰۵) |
| احراز هویت | هدر `X-API-Key` در هر درخواست |

---

## ۲. احراز هویت

هر درخواست باید هدر `X-API-Key` را با کلید معتبر داشته باشد.

```
X-API-Key: <کلید شما>
```

کلید در پنل داشبورد (بخش تنظیمات) یا در فایل `.env` سرور با نام `BOT_API_KEY` تعیین
می‌شود. برای تغییر کلید کافی است مقدار جدید بگذاری و سرویس‌ها را ری‌استارت کنی.

### کدهای وضعیت احراز هویت
| کد | معنی |
|----|------|
| `200` | موفق |
| `401` | کلید غایب یا اشتباه است |
| `403` | (رزرو) دسترسی غیرمجاز |
| `404` | منبع پیدا نشد (مثلاً محصولی با این شناسه نیست) |
| `405` | متد اشتباه (مثلاً POST زدی) |
| `429` | از سقف نرخ گذشتی (۱۲۰ درخواست در دقیقه برای هر IP) |
| `503` | API غیرفعال است (کلیدی روی سرور تنظیم نشده) |

پاسخ خطا همیشه این شکل است:
```json
{ "detail": "invalid or missing X-API-Key" }
```

---

## ۳. محدودیت نرخ (Rate Limit)

هر IP حداکثر **۱۲۰ درخواست در دقیقه** می‌تواند بزند. بعد از آن پاسخ `429` می‌گیری.
اگر ربات پرترافیک داری، درخواست‌ها را با کمی فاصله بفرست یا نتایج را کش کن.

---

## ۴. اندپوینت‌ها

### 📦 فهرست محصولات
```
GET /api/v1/products/
```
**پارامترهای اختیاری (Query):**
| پارامتر | توضیح | مثال |
|---------|-------|------|
| `q` | جست‌وجو در نام/توضیحات/برند | `?q=پیراهن` |
| `category` | فیلتر بر اساس اسلاگ دسته | `?category=shirts` |
| `brand` | فیلتر بر اساس اسلاگ برند | `?brand=nike` |
| `gender` | جنسیت (`men` / `women` / ...) | `?gender=women` |
| `page` | شمارهٔ صفحه (پیش‌فرض ۱) | `?page=2` |
| `page_size` | تعداد در صفحه (۱ تا ۵۰، پیش‌فرض ۱۰) | `?page_size=20` |

**نمونهٔ پاسخ:**
```json
{
  "count": 42,
  "page": 1,
  "pages": 5,
  "results": [
    {
      "id": 12,
      "name": "پیراهن آبی",
      "slug": "blue-shirt",
      "is_wholesale": false,
      "price": 150000,
      "original_price": 200000,
      "discount_percent": 25,
      "brand": "Nike",
      "category": "پیراهن",
      "gender": "men",
      "rating": 4.5,
      "in_stock": true,
      "image": "https://oramshop.ir/media/products/blue.jpg",
      "url": "https://oramshop.ir/product/blue-shirt/"
    }
  ]
}
```

> 🔒 **قیمت عمده‌فروشی هرگز لو نمی‌رود:** اگر محصولی `is_wholesale: true` باشد،
> مقدار `price` و `original_price` آن `null` برمی‌گردد.

---

### 📦 جزئیات یک محصول
```
GET /api/v1/products/<id>/
```
همهٔ فیلدهای بالا به‌اضافهٔ `description`، `sku`، فهرست `images` و `variants`:
```json
{
  "id": 12,
  "name": "پیراهن آبی",
  "...": "... بقیهٔ فیلدهای خلاصه ...",
  "description": "پیراهن نخی مردانه",
  "sku": "SH-1200",
  "images": [
    "https://oramshop.ir/media/products/blue-1.jpg",
    "https://oramshop.ir/media/products/blue-2.jpg"
  ],
  "variants": [
    {
      "id": 3,
      "size": "XL",
      "color": "آبی",
      "color_hex": "#0000ff",
      "stock": 5,
      "price": 150000
    }
  ]
}
```
اگر محصول وجود نداشته باشد یا غیرفعال باشد → `404`.

---

### 🏷️ فهرست دسته‌بندی‌ها
```
GET /api/v1/categories/
```
```json
{ "results": [ { "id": 1, "name": "پیراهن", "slug": "shirts" } ] }
```

---

### ™️ فهرست برندها
```
GET /api/v1/brands/
```
```json
{
  "results": [
    { "id": 1, "name": "Nike", "slug": "nike",
      "logo": "https://oramshop.ir/media/brands/nike.png" }
  ]
}
```

---

## ۵. مثال‌های اتصال

### cURL
```bash
curl -H "X-API-Key: کلید‌شما" \
     "https://oramshop.ir/api/v1/products/?q=پیراهن&page_size=5"
```

### Python (requests)
```python
import requests

BASE = "https://oramshop.ir/api/v1"
HEADERS = {"X-API-Key": "کلید‌شما"}

# فهرست محصولات با فیلتر
r = requests.get(f"{BASE}/products/",
                 headers=HEADERS,
                 params={"category": "shirts", "page": 1, "page_size": 20})
r.raise_for_status()
data = r.json()
print(data["count"], "محصول")
for p in data["results"]:
    price = p["price"] if p["price"] is not None else "عمده"
    print(p["name"], "-", price)

# جزئیات یک محصول
detail = requests.get(f"{BASE}/products/12/", headers=HEADERS).json()
```

### JavaScript (Node / مرورگر)
```javascript
const BASE = "https://oramshop.ir/api/v1";
const HEADERS = { "X-API-Key": "کلید‌شما" };

async function getProducts(query = "") {
  const res = await fetch(`${BASE}/products/?q=${encodeURIComponent(query)}`,
                          { headers: HEADERS });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

getProducts("پیراهن").then(d => console.log(d.count, "محصول"));
```

### PHP
```php
<?php
$ch = curl_init("https://oramshop.ir/api/v1/products/?page_size=10");
curl_setopt($ch, CURLOPT_HTTPHEADER, ["X-API-Key: کلید‌شما"]);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$data = json_decode(curl_exec($ch), true);
curl_close($ch);
echo $data["count"] . " محصول\n";
```

---

## ۶. نکات پیاده‌سازی برای توسعه‌دهنده

* **صفحه‌بندی:** همیشه `count`, `page`, `pages` را بخوان و تا `page == pages` جلو برو.
* **کش:** دسته‌ها و برندها کم تغییر می‌کنند؛ چند دقیقه کششان کن تا به سقف نرخ نخوری.
* **URLها مطلق‌اند:** فیلدهای `image`, `logo`, `url` کامل‌اند و نیازی به افزودن دامنه ندارند.
* **`null` را مدیریت کن:** `price`, `rating`, `brand`, `category` ممکن است `null` باشند.
* **موجودی:** برای دکمهٔ «افزودن به سبد» از `in_stock` (خلاصه) یا `variants[].stock` (جزئیات) استفاده کن.
* **امنیت کلید:** کلید API را در کد سمت کاربر (مرورگر عمومی) نگذار؛ آن را روی سرور
  خودت نگه دار و درخواست‌ها را از بک‌اند خودت پروکسی کن.

---

## ۷. ساختار فنی (برای نگهداری)

کد API در اپ `api/` قرار دارد:
```
api/
├── serializers.py   # شکل خروجی JSON (ProductSummary/Detail, Category, Brand)
├── views.py         # ویوهای کلاس‌محور DRF + گیت X-API-Key + محدودیت نرخ
└── urls.py          # مسیرها
```
* کلاس پایهٔ `BotApiView` گیت احراز هویت و نرخ را در متد `initial` اعمال می‌کند، پس
  همهٔ اندپوینت‌ها خودکار محافظت می‌شوند.
* برای افزودن اندپوینت جدید: یک سریالایزر در `serializers.py` و یک زیرکلاس از
  `BotApiView` با متد `get` بساز و در `urls.py` ثبت کن.
* افزودن اندپوینت جدید مسیرهای موجود را نمی‌شکند؛ قرارداد فعلی پایدار است.
