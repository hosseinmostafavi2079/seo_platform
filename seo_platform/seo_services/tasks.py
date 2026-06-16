import os
import json
import requests
import time
from bs4 import BeautifulSoup
from celery import shared_task
from .models import Site, KeywordResearch, GeneratedArticle, AIConfig
from .llm_service import LLMService

# ==========================================
# بخش اول: ابزارهای تصویرسازی مابین متن
# ==========================================
def generate_ai_image(site_id, feature_type, prompt_text):
    """
    تابع کمکی برای تولید تصویر با استفاده از API تصویرسازی گپ‌جی‌پتی یا اوپن‌ای‌آی
    """
    config = AIConfig.objects.filter(site_id=site_id, feature_type=feature_type).first()
    if not config or not config.api_key:
        return "https://placehold.co/1024x1024.png?text=Image+Error"
    
    if config.provider == 'gapgpt':
        url = "https://api.gapgpt.app/v1/images/generations"
        headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "imagen-4.0-ultra-generate-001",
            "prompt": prompt_text,
            "n": 1,
            "size": "1080x720"
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=90)
            if res.status_code == 200:
                data = res.json().get('data', [{}])[0]
                return data.get('url') or f"data:image/webp;base64,{data.get('b64_json')}"
        except Exception as e:
            print(f"خطا در تولید تصویر با گپ‌جی‌پتی: {str(e)}")
            
    elif config.provider == 'openai':
        url = "https://api.openai.com/v1/images/generations"
        headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
        payload = {"model": "dall-e-3", "prompt": prompt_text, "n": 1, "size": "1024x1024"}
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=90)
            if res.status_code == 200:
                return res.json().get('data', [{}])[0].get('url')
        except Exception as e:
            print(f"خطا در تولید تصویر با اوپن‌ای‌آی: {str(e)}")
            
    return "https://placehold.co/1024x1024.png?text=Generated+Image"


# ==========================================
# بخش دوم: تسک تحقیق کلمات کلیدی (فاز ۵)
# ==========================================
@shared_task
def run_keyword_research_task(site_id, business_description, core_keywords, competitors):
    """
    تسک ناهمگام برای اسکرپ رقبا، تحلیل Content Gap و استخراج کلمات و ۸۰ عنوان خوشه‌ای با هوش مصنوعی
    """
    print(f"🔐 شروع فرآیند تحقیق کلمات کلیدی برای سایت شناسه: {site_id}")
    
    serper_key = os.getenv('SERPER_API_KEY')
    search_url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
    payload = {
        "q": f"{core_keywords} -site:digikala.com -site:aparat.com",
        "gl": "ir",
        "hl": "fa"
    }
    
    context_text = ""
    try:
        search_res = requests.post(search_url, headers=headers, json=payload, timeout=15)
        if search_res.status_code == 200:
            results = search_res.json().get('organic', [])[:3]
            
            for idx, item in enumerate(results):
                link = item.get('link')
                try:
                    page_res = requests.get(link, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                    if page_res.status_code == 200:
                        soup = BeautifulSoup(page_res.text, 'html.parser')
                        for script in soup(["script", "style"]):
                            script.extract()
                        
                        page_text = soup.get_text()
                        lines = (line.strip() for line in page_text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        clean_text = " ".join(chunk for chunk in chunks if chunk)[:1200]
                        
                        context_text += f"\n\n# منبع رقیب {idx+1}: {link}\nساختار هدینگ‌ها و متن رقیب:\n{clean_text}"
                except Exception as e:
                    print(f"خطا در استخراج دیتای لینک {link}: {str(e)}")
    except Exception as e:
        print(f"خطا در ارتباط با Serper API: {str(e)}")

    system_message = (
        "شما یک معمار ارشد سئو و استراتژیست محتوای چند حوزه‌ای هستید که بر اساس مدل Topic Clusters معماری محتوا می‌سازید.\n"
        "وظیفه شما تولید یک خروجی دقیق و فقط در قالب ساختار JSON معتبر است.\n"
        "قوانین سخت‌گیرانه:\n"
        "1. بخش keywords: حداقل ۱۰ ترکیب کلمه اصلی و طولانی به همراه Search Intent دقیق (Informational, Commercial, Transactional, Navigational).\n"
        "2. بخش categories: حداقل ۵ دسته‌بندی وسیع Pillar Page برای ساخت صفحات مادر.\n"
        "3. بخش topics: حداقل ۸۰ عنوان مقاله خوشه‌ای با جذابیت بالا (CTR بالا) و حداکثر ۱۴ کلمه.\n"
        "نکته: هر عنوان مقاله در بخش topics باید دقیقاً به یکی از پنج دسته‌بندی بخش categories متصل شده باشد.\n"
        "خروجی شما باید فاقد هرگونه متن توضیحی، کدهای جاوامک یا بلاک‌کد اضافه خارج از ساختار JSON باشد.\n\n"
        "قالب خروجی معتبر:\n"
        "{\n"
        '  "keywords": [{"keyword": "کلمه ۱", "intent": "Informational"}],\n'
        '  "categories": ["دسته ۱", "دسته ۲"],\n'
        '  "topics": [{"title": "عنوان مقاله مرتبط با دسته ۱", "category": "دسته ۱"}]\n'
        "}"
    )
    
    user_message = (
        f"شرح کسب و کار ما: {business_description}\n"
        f"کلمات کلیدی اصلی مد نظر ما: {core_keywords}\n"
        f"آدرس رقبا: {competitors}\n"
        f"دیتای استخراج شده زنده از صفحات رقبای رتبه برتر گوگل:\n{context_text}"
    )

    try:
        ai_raw_response = LLMService.send_request(
            site_id=site_id,
            feature_type='keyword',
            system_message=system_message,
            user_message=user_message
        )
        
        clean_json_str = ai_raw_response.strip()
        if "```json" in clean_json_str:
            clean_json_str = clean_json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json_str:
            clean_json_str = clean_json_str.split("```")[1].split("```")[0].strip()

        data = json.loads(clean_json_str)
        site_instance = Site.objects.get(id=site_id)
        
        keywords_intent_map = {k['keyword']: k['intent'] for k in data.get('keywords', [])}
        main_keyword = core_keywords.split('،')[0] if '،' in core_keywords else core_keywords
        
        topics_built = data.get('topics', [])
        for item in topics_built:
            title = item.get('title')
            category = item.get('category')
            
            detected_intent = 'Informational'
            for kw, intent in keywords_intent_map.items():
                if kw in title:
                    detected_intent = intent
                    break
            
            KeywordResearch.objects.create(
                site=site_instance,
                keyword=main_keyword,
                intent=detected_intent,
                category_pillar=category,
                article_title=title,
                status='pending'
            )
            
        print(f"✅ فرآیند کیورد ریسرچ پایان یافت. {len(topics_built)} عنوان مقاله ثبت شد.")
        return f"موفقیت‌آمیز: تعداد {len(topics_built)} عنوان مقاله به بانک کلمات کلیدی اضافه شد."
        
    except Exception as e:
        print(f"❌ خطا در پردازش تسک هوش مصنوعی: {str(e)}")
        return f"شکست در فرآیند: {str(e)}"


# ==========================================
# بخش سوم: تسک تولید مقاله سئو شده (فاز ۶)
# ==========================================
@shared_task
def run_article_generation_task(article_id):
    """
    تسک اصلی تولید مقاله: استخراج لینک‌های داخلی وردپرس، تولید متن سئو شده، درج تصاویر داخلی و ذخیره پیش‌نویس
    """
    try:
        article = GeneratedArticle.objects.get(id=article_id)
        site = article.site
        
        formatted_links = "لیست مقالات موجود برای لینک‌دهی داخلی:\n"
        try:
            wp_res = requests.get(f"{site.wp_url.rstrip('/')}/wp-json/wp/v2/posts?per_page=40&status=publish", timeout=15)
            if wp_res.status_code == 200:
                for post in wp_res.json():
                    formatted_links += f"- {post.get('title', {}).get('rendered')}: {post.get('link')}\n"
        except Exception as e:
            print(f"امکان دریافت لینک‌های وردپرس وجود نداشت: {str(e)}")

        image_instruction = ""
        if article.image_count > 0:
            image_instruction = (
                f"شما باید دقیقاً تعداد {article.image_count} بار در نقاط حساس و زیر تیترهای H2 مقاله، "
                f"عبارت دقیق `` را قرار دهید تا سیستم بتواند تصاویر اختصاصی را جایگزین کند."
            )
        else:
            image_instruction = "هیچ نشانه یا تگ تصویری در میان متن قرار ندهید."

        system_message = (
            f"شما نویسنده محتوای خلاق و متخصص سئو بین‌المللی هستید. لحن شما رسمی اما جذاب است.\n"
            f"طول مقاله باید حداقل ۱۵۰۰ کلمه باشد و الزامات زیر را دقیقاً در قالب خروجی JSON معتبر رعایت کنید:\n"
            f"1. کلمات کلیدی را به صورت انکرتکست‌های کاملاً طبیعی با استفاده از این لیست لینک‌سازی کنید:\n{formatted_links}\n"
            f"2. {image_instruction}\n"
            f"3. بخش سؤالات متداول (FAQ) شامل ۳ تا ۵ پرسش و پاسخ با تگ H2 و H3 در انتهای مقاله الزامی است.\n"
            f"خروجی باید صرفاً یک آبجکت JSON بدون تگ‌های اضافی مارک‌داون یا توضیحات متنی قبل و بعد باشد.\n\n"
            f"ساختار دقیق خروجی مورد انتظار:\n"
            "{\n"
            '  "slug": "short-english-slug",\n'
            '  "title": "عنوان سئو شده مقاله",\n'
            '  "seo_title": "عنوان متای سئو (رنک مث / یوست)",\n'
            '  "seo_description": "توضیحات متای سئو با رعایت طول استاندارد",\n'
            '  "content": "متن کامل مقاله با فرمت مشخص HTML یا Markdown همراه با لینک‌ها و پلیس‌هولدرهای تصویر"\n'
            "}"
        )

        user_message = f"لطفاً بر اساس عنوان پیشنهادی خوشه محتوایی «{article.title}»، یک مقاله سئو شده و شاهکار خلق کنید."

        ai_response = LLMService.send_request(
            site_id=site.id,
            feature_type='article',
            system_message=system_message,
            user_message=user_message
        )

        clean_json_str = ai_response.strip()
        if "```json" in clean_json_str:
            clean_json_str = clean_json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_json_str:
            clean_json_str = clean_json_str.split("```")[1].split("```")[0].strip()

        data = json.loads(clean_json_str)

        img_prompt = f"A professional high-fidelity editorial tech vector illustration for an article titled: {data.get('title')}, modern colors, corporate clean background."
        featured_image = generate_ai_image(site.id, 'article', img_prompt)

        final_content = data.get('content', '')
        if article.image_count > 0 and "" in final_content:
            for i in range(article.image_count):
                mid_img_prompt = f"A clean minimal presentation graphic chart or illustrative object matching the context of article: {data.get('title')} part {i+1}, web design style."
                generated_mid_url = generate_ai_image(site.id, 'article', mid_img_prompt)
                img_tag = f'<img src="{generated_mid_url}" alt="{data.get("title")}" style="width:100%; max-width:800px; display:block; margin:20px auto; border-radius:8px;" />'
                final_content = final_content.replace("", img_tag, 1)

        article.slug = data.get('slug', article.slug)
        article.title = data.get('title', article.title)
        article.seo_title = data.get('seo_title', '')
        article.seo_description = data.get('seo_description', '')
        article.content = final_content
        article.featured_image_url = featured_image
        article.status = 'draft'
        article.save()

        print(f"✅ مقاله شناسه {article_id} با موفقیت تولید و در بانک پلتفرم ذخیره شد.")
        return "موفقیت‌آمیز: مقاله و تصاویر مابین آن تولید و آماده تایید نهایی هستند."

    except Exception as e:
        print(f"❌ خطا در کارخانه تولید مقاله: {str(e)}")
        return f"شکست: {str(e)}"