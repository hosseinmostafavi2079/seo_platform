# apps/keyword_research/tasks.py
import json
import re
from django.utils import timezone
from config.celery import app
from keyword_research.models import KeywordResearchJob, KeywordCategory, Keyword, ContentTopic
from keyword_research.scrapers import CompetitorScraper
from ai_providers.models import GenerationProfile
from ai_providers.services.factory import AIClientFactory

@app.task(name="keyword_research.run_job")
def run_keyword_research_task(job_id):
    try:
        job = KeywordResearchJob.objects.get(id=job_id)
    except KeywordResearchJob.DoesNotExist:
        return f"Job {job_id} not found."

    job.status = 'running'
    job.save()

    try:
        # ۱. اسکرپ صفحات رقبا در صورت وجود
        competitor_context = ""
        if job.competitor_urls:
            competitor_context = CompetitorScraper.scrape_headings(job.competitor_urls)

        # ۲. واکشی پروفایل و کلاینت هوش مصنوعی پیش‌فرض سایت
        try:
            profile = GenerationProfile.objects.get(site=job.site)
            ai_config = profile.ai_config
        except GenerationProfile.DoesNotExist:
            # فال‌بک به اولین کانفیگ فعال سایت یا گلوبال
            ai_config = job.site.ai_configs.filter(is_active=True).first()
            if not ai_config:
                from ai_providers.models import AIProviderConfig
                ai_config = AIProviderConfig.objects.filter(site=None, is_active=True).first()

        if not ai_config:
            raise ValueError("No active AI Provider Configuration found for this site or global fallback.")

        ai_client = AIClientFactory.get_client(ai_config)

        # ۳. داینامیک‌سازی تعداد نتایج بر اساس دکمه عمق فرم
        count_map = {'basic': 15, 'standard': 45, 'deep': 85}
        target_count = count_map.get(job.depth_option, 45)

        # ۴. مهندسی ساختاریافته پرامپت سئو با تضمین خروجی کدهای معتبر JSON
        system_prompt = (
            "You are an expert SEO Strategist. Analyze the given business information and keywords. "
            "You MUST reply with a JSON object ONLY, strictly matching this exact schema:\n"
            "{\n"
            "  \"categories\": [\"Category Title 1\", \"Category Title 2\"],\n"
            "  \"keywords\": [\n"
            "     {\"keyword\": \"string\", \"intent\": \"informational|commercial|transactional|navigational\", \"notes\": \"string\"}\n"
            "  ],\n"
            "  \"topics\": [\n"
            "     {\"title\": \"SEO Friendly Article Title\", \"target_keyword\": \"string\", \"category\": \"Category Title 1\"}\n"
            "  ]\n"
            "}\n"
            "Do not include markdown blocks like ```json ... ``` inside your string output. Return pure minified text."
        )

        user_content = (
            f"Business Description: {job.business_description}\n"
            f"Seed Keywords: {job.seed_keywords}\n"
            f"Target Topic Count: Around {target_count}\n"
        )
        if job.domain_focus:
            user_content += f"Special Focus/Niche: {job.domain_focus}\n"
        if competitor_context:
            user_content += f"\nCompetitor Heading Content (Content Gap Data):\n{competitor_context}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        # ۵. فرستادن درخواست به لایه کلاینت هوش مصنوعی
        ai_response = ai_client.chat_completion(
            messages=messages,
            temperature=0.6,
            max_tokens=4000
        )

        raw_text = ai_response["text"].strip()
        
        # مکانیزم امنیتی اعتبارسنجی JSON با Fallback Regex (کد توسعه‌یافته نیت ایزوله شما)
        try:
            clean_json_str = raw_text
            if "```" in raw_text:
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if match:
                    clean_json_str = match.group(0)
            parsed_data = json.loads(clean_json_str)
        except Exception as json_err:
            raise ValueError(f"AI response was not valid JSON format. Raw response snapshot: {raw_text[:200]}")

        # ۶. ذخیره‌سازی داده‌ها در دیتابیس با وضعیت تایید نشده (Pending Approval)
        job.raw_ai_output = parsed_data
        
        # ذخیره دسته‌بندی‌ها به صورت Map برای اتصال به کلمات کلیدی و موضوعات
        category_objects_map = {}
        for cat_title in parsed_data.get('categories', []):
            cat, _ = KeywordCategory.objects.get_or_create(job=job, site=job.site, title=cat_title)
            category_objects_map[cat_title] = cat

        for kw_data in parsed_data.get('keywords', []):
            Keyword.objects.create(
                job=job,
                site=job.site,
                keyword=kw_data.get('keyword', ''),
                intent=kw_data.get('intent', 'informational'),
                notes=kw_data.get('notes', '')
            )

        for topic_data in parsed_data.get('topics', []):
            cat_obj = category_objects_map.get(topic_data.get('category'))
            ContentTopic.objects.create(
                job=job,
                site=job.site,
                category=cat_obj,
                title=topic_data.get('title', ''),
                target_keyword=topic_data.get('target_keyword', '')
            )

        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save()
        return f"Job {job_id} executed successfully."

    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.save()
        return f"Job {job_id} failed: {str(e)}"