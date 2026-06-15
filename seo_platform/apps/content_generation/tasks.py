# apps/content_generation/tasks.py
import json
import re
import io
from django.core.files.base import ContentFile
from config.celery import app
from content_generation.models import ArticleJob
from content_generation.services.wordpress_client import WordPressClient
from ai_providers.models import GenerationProfile
from ai_providers.services.factory import AIClientFactory

# وارد کردن متد کمکی Pillow برای فشرده‌سازی WebP
try:
    from PIL import Image
except ImportError:
    Image = None

@app.task(name="content_generation.generate_article")
def generate_article_task(job_id):
    try:
        job = ArticleJob.objects.get(id=job_id)
    except ArticleJob.DoesNotExist:
        return f"ArticleJob {job_id} not found."

    job.status = 'generating'
    job.save()

    try:
        wp_client = WordPressClient(job.site)
        
        # ۱. استخراج پست‌های موجود برای تحلیل لینک‌سازی داخلی (کد اختصاصی Logic Javascript1 شما)
        existing_posts = wp_client.fetch_existing_posts()
        links_context = ""
        if existing_posts:
            links_context = "\n".join([f"- Title: {p['title']} | URL: {p['url']}" for p in existing_posts[:15]])

        # ۲. لود تنظیمات لایه هوش مصنوعی سایت
        profile = GenerationProfile.objects.get(site=job.site)
        ai_client = AIClientFactory.get_client(profile.ai_config)

        # ۳. مهندسی پرامپت تولید مقاله سئومحور ساختاریافته
        system_prompt = (
            f"You are an Elite SEO Copywriter. Write a comprehensive article in Persian. "
            f"Tone of voice: {profile.tone_of_voice}. "
            f"You MUST include exactly {job.images_count} image placeholders directly in the HTML text body where appropriate "
            f"using exactly this string format: where X is the index starting from 1.\n"
            f"You must return a JSON object with this structure:\n"
            "{\n"
            "  \"content_html\": \"...\",\n"
            "  \"seo_title\": \"...\",\n"
            "  \"seo_meta_description\": \"...\",\n"
            "  \"seo_focus_keyword\": \"...\",\n"
            "  \"image_prompts\": [\"Detailed prompt for AI image generation 1\", \"... Selection matches count\"]\n"
            "}"
        )

        user_prompt = (
            f"Topic/Title: {job.title}\n"
            f"Target Keyword: {job.target_keyword}\n"
            f"Target Word Count: {profile.target_word_count} words.\n"
            f"Custom Instructions: {job.custom_instructions or profile.custom_instructions}\n"
        )
        if links_context:
            user_prompt += (
                f"\nINTERNAL LINKING TASK:\nNaturally inject between {profile.internal_links_min} and "
                f"{profile.internal_links_max} hyperlinks from the list below using real contextual anchor texts:\n"
                f"{links_context}\n"
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        ai_response = ai_client.chat_completion(messages, temperature=0.7, max_tokens=profile.max_tokens)
        raw_text = ai_response["text"].strip()

        # استخراج ایمن آوت‌پوت JSON
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        parsed_data = json.loads(match.group(0) if match else raw_text)

        job.content_html = parsed_data.get('content_html', '')
        job.seo_title = parsed_data.get('seo_title', '')
        job.seo_meta_description = parsed_data.get('seo_meta_description', '')
        job.seo_focus_keyword = parsed_data.get('seo_focus_keyword', job.target_keyword)
        job.ai_config_used = profile.ai_config

        # ۴. پردازش، تبدیل و آپلود تصاویر به صورت موازی (در صورت وجود پرامپت تصویر)
        image_prompts = parsed_data.get('image_prompts', [])
        uploaded_media_ids = []
        inline_image_paths = []

        for idx, img_prompt in enumerate(image_prompts[:job.images_count]):
            try:
                # فراخوانی متد استراتژی تولید تصویر کلاینت
                raw_img_bytes = ai_client.generate_image(prompt=img_prompt)
                
                # فشرده‌سازی با Pillow و تبدیل کانتینری به WebP با حفظ حریم حافظه سرور
                if Image:
                    image = Image.open(io.BytesIO(raw_img_bytes))
                    output_bytes = io.BytesIO()
                    image.save(output_bytes, format="WEBP", quality=82)
                    processed_bytes = output_bytes.getvalue()
                else:
                    processed_bytes = raw_img_bytes

                # آپلود به مدیا وردپرس
                media_id = wp_client.upload_media(processed_bytes, f"article_{job_id}_{idx+1}.webp")
                uploaded_media_ids.append(media_id)
                
                # رپلیس کردن پلیس‌هولدر داخل کد HTML متن با تگ اصلی تصویر آپلود شده
                # توجه: در یک پروژه واقعی آدرس کامل تصویر برگشت داده می‌شود، اینجا شناسه را رپلیس می‌کنیم یا تگ تصویر وردپرسی ستاپ می‌شود
                wp_img_tag = f'<figure class="wp-block-image"><img src="{media_id}" alt="{job.seo_focus_keyword}"/></figure>'
                job.content_html = job.content_html.replace(f"", wp_img_tag)
                inline_image_paths.append(f"wp-media-id:{media_id}")
            except Exception:
                pass

        job.inline_images = inline_image_paths
        job.status = 'ready_for_review'  # تغییر وضعیت به منتظر بازبینی در داشبورد
        job.save()
        return f"Article {job_id} generated and ready for review."

    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.save()
        return f"Article {job_id} generation failed: {str(e)}"