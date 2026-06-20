# استخدام نسخة بايثون رسمية ومستقرة ومبنية على نظام دبيان الكامل وليس الـ Alpine الضعيف
FROM python:3.11-slim-bookworm

# تثبيت حزم النظام والمترجمات المطلوبة لبناء greenlet والمكتبات الأخرى
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# إعداد مجلد العمل داخل السيرفر
WORKDIR /app

# نسخ ملف المكتبات أولاً وتثبيته
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# تثبيت متصفح Chromium وحزم الحماية الخاصة بـ Playwright داخل النظام
RUN playwright install chromium --with-deps

# نسخ بقية ملفات الكود (مثل bot.py) إلى السيرفر
COPY . .

# أمر تشغيل البوت عند إطلاق السيرفر
CMD ["python", "bot.py"]
