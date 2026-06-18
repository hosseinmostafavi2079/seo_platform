import os
import json
import requests
import base64
from bs4 import BeautifulSoup
from celery import shared_task
from .models import Site, KeywordResearch, GeneratedArticle, AIConfig
from .llm_service import LLMService

# توکن ثابت برای جایگذاری دقیق تصاویر مابین متن
IMAGE_TOKEN = "[MID_IMAGE_PLACEHOLDER]"

def clean_and_parse_json(raw_text):
    """ پاک‌سازی نشانه‌گذارهای مارک‌داون و پارس امن جی‌سان """
    text = raw_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)

# ==========================================
# ابزار کمکی: آپلود مستقیم تصاویر به گالری رسانه وردپرس
# ==========================================
def upload_image_to_wordpress(site, image_source, title="seo-media-asset"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Disposition": f'attachment; filename="{title}.webp"'
    }
    img_bytes = b""
    
    try:
        if "base64," in image_source:
            b64_data = image_source.split("base64,")[1]
            img_bytes = base64.b64decode(b64_data)
            headers["Content-Type"] = "image/webp"
        else:
            res = requests.get(image_source, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                img_bytes = res.content
                headers["Content-Type"] = res.headers.get("Content-Type", "image/jpeg")

        if img_bytes:
            wp_res = requests.post(
                f"{site.wp_url.rstrip('/')}/wp-json/wp/v2/media",
                auth=(site.wp_username, site.wp_app_password),
                headers=headers,
                data=img_bytes,
                timeout=35
            )
            if wp_res.status_code in [200, 201]:
                res_json = wp_res.json()
                return res_json.get('source_url'), res_json.get('id')
            else:
                print(f"WP Media API rejected upload: {wp_res.status_code} - {wp_res.text}")
    except Exception as e:
        print(f"Error calling WP Media API: {str(e)}")
        
    if "base64," in image_source:
        return "[https://placehold.co/1024x1024.png?text=WordPress+Media+Upload+Failed](https://placehold.co/1024x1024.png?text=WordPress+Media+Upload+Failed)", None
    return image_source, None


# ==========================================
# بخش اول: ابزارهای تصویرسازی مابین متن
# ==========================================
def generate_ai_image(site_id, prompt_text):
    config = AIConfig.objects.filter(site_id=site_id, feature_type='article_image').first()
    if not config:
        raise Exception("تنظیمات تولید تصویر (article_image) برای این سایت یافت نشد.")
    if not config.api_key:
        raise Exception("کلید API تصویرساز در تنظیمات سایت شما ثبت نشده است.")
    
    if config.provider == 'gapgpt':
        url = "[https://api.gapgpt.app/v1/images/generations](https://api.gapgpt.app/v1/images/generations)"
        headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
        payload = {"model": config.model_name, "prompt": prompt_text, "n": 1, "size": "1080x720"}
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=90)
            if res.status_code == 200:
                data = res.json().get('data', [{}])[0]
                val = data.get('url') or (f"data:image/webp;base64,{data.get('b64_json')}" if data.get('b64_json') else None)
                if val: return val
                raise Exception("پاسخ دریافتی از GapGPT فاقد فیلد تصویر بود.")
            else:
                raise Exception(f"خطای سرور GapGPT: {res.text}")
        except Exception as e:
            raise Exception(f"خطا در ارتباط با تصویرساز گپ‌جی‌پتی: {str(e)}")
            
    elif config.provider == 'openai':
        url = "[https://api.openai.com/v1/images/generations](https://api.openai.com/v1/images/generations)"
        headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
        payload = {"model": "dall-e-3", "prompt": prompt_text, "n": 1, "size": "1024x1024"}
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=90)
            if res.status_code == 200:
                val = res.json().get('data', [{}])[0].get('url')
                if val: return val
                raise Exception("پاسخ دریافتی از OpenAI فاقد آدرس تصویر بود.")
            else:
                raise Exception(f"خطای سرور OpenAI: {res.text}")
        except Exception as e:
            raise Exception(f"خطا در ارتباط با تصویرساز دال‌ای: {str(e)}")
            
    raise Exception(f"پرووایدر تصویرساز نامعتبر است: {config.provider}")


# ==========================================
# بخش دوم: تسک تولید مقاله سئو شده و ارسال به وردپرس
# ==========================================
@shared_task
def run_article_generation_task(article_id):
    article = GeneratedArticle.objects.get(id=article_id)
    site = article.site
    article.error_log = None
    article.save()

    # 🔗 مرحله ۱: استخراج لینک‌های داخلی با افزایش سقف به ۱۰۰ پست برای پوشش کامل
    try:
        article.current_step = 'links'
        article.save()
        
        formatted_links = "لیست مقالات موجود برای لینک‌دهی داخلی:\n"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        wp_res = requests.get(
            f"{site.wp_url.rstrip('/')}/wp-json/wp/v2/posts?per_page=100&status=publish",
            auth=(site.wp_username, site.wp_app_password),
            headers=headers,
            timeout=15
        )
        if wp_res.status_code == 200:
            for post in wp_res.json():
                formatted_links += f"- {post.get('title', {}).get('rendered')}: {post.get('link')}\n"
        else:
            raise Exception(f"کد وضعیت نامعتبر از وردپرس دریافت شد: {wp_res.status_code}")
    except Exception as e:
        article.current_step = 'failed'
        article.error_log = f"مرحله ۱ (لینک‌سازی داخلی شکست خورد): {str(e)}"
        article.save()
        return

    # ✍️ مرحله ۲: نگارش متن و اصلاح نشانه‌گذار اختصاصی تصاویر مابین متن
    try:
        article.current_step = 'text'
        article.save()
        
        image_instruction = ""
        if article.image_count > 0:
            image_instruction = f"شما باید دقیقاً تعداد {article.image_count} بار در نقاط حساس متن بدنه HTML عبارت {IMAGE_TOKEN} را درج کنید."

        system_message = (
            f"شما یک نویسنده ارشد سئو هستید. ساختار محتوا باید کاملاً منطبق بر نوع لحن و استراتژی: '{site.get_content_type_display()}' باشد.\n"
            f"طول مقاله حداقل ۱۵۰۰ کلمه و ساختار خروجی الزاماً فرمت JSON زیر باشد:\n"
            "{\n"
            '  "slug": "english-slug",\n'
            '  "title": "عنوان",\n'
            '  "seo_title": "عنوان متا",\n'
            '  "seo_description": "توضیحات متا",\n'
            '  "content": "بدنه اصلی HTML"\n'
            "}\n"
            f"قوانین مهم: کلمات کلیدی را به صورت انکرتکست طبیعی با این لیست لینک‌سازی کنید:\n{formatted_links}\n{image_instruction}"
        )
        
        user_message = f"لطفاً یک مقاله شاهکار، جامع و سئو شده برای موضوع عمیق «{article.title}» خلق کنید."
        
        ai_response = LLMService.send_request(
            site_id=site.id, feature_type='article_text', system_message=system_message, user_message=user_message
        )
        
        data = clean_and_parse_json(ai_response)
    except Exception as e:
        article.current_step = 'failed'
        article.error_log = f"مرحله ۲ (نگارش متن با هوش مصنوعی شکست خورد): {str(e)}"
        article.save()
        return

    # 🖼️ مرحله ۳: طراحی تصاویر اختصاصی مدیا و سایدلود به وردپرس
    try:
        article.current_step = 'images'
        article.save()
        
        img_prompt = (
            f"A realistic, photorealistic high-fidelity professional photograph completely relevant to the topic: '{data.get('title')}', "
            f"clean commercial product/tech composition, dramatic cinematic studio lighting, highly detailed 8k, "
            f"strictly NO text, NO words, NO typography, NO letters, NO writing."
        )
        raw_featured_image = generate_ai_image(site.id, img_prompt)
        featured_image, featured_image_id = upload_image_to_wordpress(site, raw_featured_image, f"featured-{data.get('slug', 'asset')}")
    except Exception as e:
        article.current_step = 'failed'
        article.error_log = f"مرحله ۳ (تصویرسازی شکست خورد): {str(e)}"
        article.save()
        return

    # 📦 مرحله ۴: مونتاژ نهایی و ارسال مستقیم پیش‌نویس به وردپرس
    try:
        article.current_step = 'assembly'
        article.save()
        
        final_content = data.get('content', '')
        if article.image_count > 0 and IMAGE_TOKEN in final_content:
            for i in range(article.image_count):
                mid_prompt = (
                    f"A high-resolution authentic real-world photograph asset closely matching the context of article part {i+1}: '{data.get('title')}', "
                    f"professional lighting, sharp focus, strictly NO text, NO typography, NO words, NO labels."
                )
                raw_mid_url = generate_ai_image(site.id, mid_prompt)
                wp_mid_url, _ = upload_image_to_wordpress(site, raw_mid_url, f"mid-{i+1}-{data.get('slug', 'asset')}")
                
                img_tag = f'<img src="{wp_mid_url}" alt="{data.get("title")}" style="width:100%; max-width:750px; display:block; margin:25px auto; border-radius:12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);" />'
                final_content = final_content.replace(IMAGE_TOKEN, img_tag, 1)
                
        article.slug = data.get('slug', article.slug)
        article.title = data.get('title', article.title)
        article.seo_title = data.get('seo_title', '')
        article.seo_description = data.get('seo_description', '')
        article.content = final_content
        article.featured_image_url = featured_image

        wp_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        wp_payload = {
            "title": article.title,
            "content": final_content,
            "slug": article.slug,
            "status": "draft"
        }
        
        if featured_image_id:
            wp_payload["featured_media"] = featured_image_id
        
        wp_post_res = requests.post(
            f"{site.wp_url.rstrip('/')}/wp-json/wp/v2/posts",
            auth=(site.wp_username, site.wp_app_password),
            headers=wp_headers,
            json=wp_payload,
            timeout=25
        )
        
        if wp_post_res.status_code in [200, 201]:
            article.wp_post_id = wp_post_res.json().get('id')
            article.status = 'sent_to_wp'
        else:
            raise Exception(f"وردپرس مقاله را نپذیرفت: {wp_post_res.status_code} - {wp_post_res.text}")

        if article.keyword_ref:
            article.keyword_ref.status = 'generated'
            article.keyword_ref.save()

        article.current_step = 'success'
        article.save()
    except Exception as e:
        article.current_step = 'failed'
        article.error_log = f"مرحله ۴ (مونتاژ و انتشار روی وردپرس شکست خورد): {str(e)}"
        article.save()


# ==========================================
# تسک ناهمگام تحقیق کلمات کلیدی (فاز ۵)
# ==========================================
@shared_task
def run_keyword_research_task(site_id, business_description, core_keywords, competitors, topic_count=20, intent_filter='All'):
    site_instance = Site.objects.get(id=site_id)
    site_instance.keyword_error_log = None
    
    try:
        site_instance.keyword_current_step = 'serper'
        site_instance.save()
        
        serper_key = os.getenv('SERPER_API_KEY')
        search_url = "[https://google.serper.dev/search](https://google.serper.dev/search)"
        headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
        payload = {"q": f"{core_keywords} -site:digikala.com -site:aparat.com", "gl": "ir", "hl": "fa"}
        
        context_text = ""
        search_res = requests.post(search_url, headers=headers, json=payload, timeout=15)
        if search_res.status_code == 200:
            results = search_res.json().get('organic', [])[:3]
            for idx, item in enumerate(results):
                link = item.get('link')
                try:
                    page_res = requests.get(link, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                    if page_res.status_code == 200:
                        soup = BeautifulSoup(page_res.text, 'html.parser')
                        for script in soup(["script", "style"]): script.extract()
                        page_text = soup.get_text()
                        lines = (line.strip() for line in page_text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        clean_text = " ".join(chunk for chunk in chunks if chunk)[:1200]
                        context_text += f"\n\n# منبع رقیب {idx+1}: {link}\nمتن:\n{clean_text}"
                except Exception:
                    pass
    except Exception as e:
        site_instance.keyword_current_step = 'failed'
        site_instance.keyword_error_log = f"خطا در مرحله ۱ (اسکرپ رقبا): {str(e)}"
        site_instance.save()
        return

    try:
        site_instance.keyword_current_step = 'llm'
        site_instance.save()

        intent_instruction = "شامل تمامی اهداف جستجو (Informational, Commercial, Transactional)"
        if intent_filter != 'All':
            intent_instruction = f"تمرکز مطلق فقط بر روی هدف جستجوی نوع: {intent_filter}"

        system_message = (
            "شما یک معمار ارشد سئو هستید که بر اساس مدل Topic Clusters ساختار محتوا طراحی می‌کنید.\n"
            "وظیفه شما تولید یک خروجی دقیق و فقط در قالب ساختار JSON معتبر است.\n"
            f"1. بخش keywords: حداقل ۱۰ ترکیب کلمه کلیدی طولانی مرتبط.\n"
            f"2. بخش categories: حداقل ۵ دسته‌بندی وسیع برای ساخت صفحات Pillar.\n"
            f"3. بخش topics: شما باید دقیقاً و الزاماً تعداد {topic_count} عنوان مقاله خوشه‌ای متمایز تولید کنید.\n"
            f"4. استراتژی اینتنت: {intent_instruction}\n"
            "قالب خروجی:\n"
            "{\n"
            '  "keywords": [{"keyword": "کلمه", "intent": "Informational"}],\n'
            '  "categories": ["دسته ۱"],\n'
            '  "topics": [{"title": "عنوان مقاله سئو شده مرتبط", "category": "دسته ۱"}]\n'
            "}"
        )
        user_message = f"شرح کسب و کار: {business_description}\nکلمات کلیدی مد نظر: {core_keywords}\nرقبا: {competitors}\nدیتای زنده رقبا:\n{context_text}"

        ai_raw_response = LLMService.send_request(
            site_id=site_id, feature_type='keyword', system_message=system_message, user_message=user_message
        )
        data = clean_and_parse_json(ai_raw_response)
    except Exception as e:
        site_instance.keyword_current_step = 'failed'
        site_instance.keyword_error_log = f"خطا در مرحله ۲ (پردازش هوش مصنوعی): {str(e)}"
        site_instance.save()
        return

    try:
        site_instance.keyword_current_step = 'saving'
        site_instance.save()
        
        keywords_intent_map = {k['keyword']: k['intent'] for k in data.get('keywords', [])}
        main_keyword = core_keywords.split('،')[0] if '،' in core_keywords else core_keywords
        
        topics_built = data.get('topics', [])
        for item in topics_built:
            title = item.get('title')
            category = item.get('category')
            
            detected_intent = intent_filter if intent_filter != 'All' else 'Informational'
            if intent_filter == 'All':
                for kw, intent in keywords_intent_map.items():
                    if kw in title:
                        detected_intent = intent
                        break
            
            KeywordResearch.objects.create(
                site=site_instance, keyword=main_keyword, intent=detected_intent,
                category_pillar=category, article_title=title, status='pending'
            )
            
        site_instance.keyword_current_step = 'success'
        site_instance.save()
    except Exception as e:
        site_instance.keyword_current_step = 'failed'
        site_instance.keyword_error_log = f"خطا در مرحله ۳ (ذخیره‌سازی داده‌ها): {str(e)}"
        site_instance.save()