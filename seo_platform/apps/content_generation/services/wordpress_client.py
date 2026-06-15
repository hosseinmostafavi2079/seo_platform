# apps/content_generation/services/wordpress_client.py
import base64
import httpx
from sites.models import Site

class WordPressClient:
    def __init__(self, site: Site):
        self.site = site
        self.base_url = site.wp_api_url.rstrip('/')
        # ایجاد هدر احراز هویت Basic با استفاده از Application Password سایت
        credentials = f"{site.wp_username}:{site.wp_app_password}"
        encoded_creds = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_creds}"
        }

    def fetch_existing_posts(self, limit: int = 40) -> list:
        """واکشی مقالات منتشر شده جهت استخراج لینک‌های داخلی (کاهش ریکوئست با انتخاب فیلدهای محدود)"""
        url = f"{self.base_url}/wp/v2/posts"
        params = {"status": "publish", "per_page": limit, "_fields": "title,link"}
        try:
            with httpx.Client(timeout=15.0, headers=self.headers, verify=False) as client:
                res = client.get(url, params=params)
                if res.status_code == 200:
                    return [{"title": p["title"]["rendered"], "url": p["link"]} for p in res.json()]
        except Exception:
            pass
        return []

    def upload_media(self, file_bytes: bytes, filename: str) -> int:
        """آپلود تصویر به بخش رسانه‌های وردپرس و بازگرداندن Media ID"""
        url = f"{self.base_url}/wp/v2/media"
        headers = {
            **self.headers,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/webp"
        }
        with httpx.Client(timeout=30.0, headers=headers, verify=False) as client:
            res = client.post(url, content=file_bytes)
            res.raise_for_status()
            return res.json()["id"]

    def create_draft_post(self, title: str, content: str, category_id: int, seo_data: dict, featured_media_id: int = None) -> int:
        """ایجاد پست به صورت Draft و تزریق متادیتای افزونه‌های سئو (RankMath / Yoast)"""
        url = f"{self.base_url}/wp/v2/posts"
        
        payload = {
            "title": title,
            "content": content,
            "status": "draft",
        }
        if category_id:
            payload["categories"] = [category_id]
        if featured_media_id:
            payload["featured_media"] = featured_media_id

        # بررسی و تزریق متادیتای سئو بر اساس افزونه فعال سایت
        meta = {}
        plugin = seo_data.get('plugin', 'rankmath')
        if plugin == 'rankmath':
            meta["rank_math_title"] = seo_data.get('seo_title', title)
            meta["rank_math_description"] = seo_data.get('meta_description', '')
            meta["rank_math_focus_keyword"] = seo_data.get('focus_keyword', '')
        else: # Yoast SEO
            meta["_yoast_wpseo_title"] = seo_data.get('seo_title', title)
            meta["_yoast_wpseo_metadesc"] = seo_data.get('meta_description', '')
            meta["_yoast_wpseo_focuskw"] = seo_data.get('focus_keyword', '')
            
        payload["meta"] = meta

        with httpx.Client(timeout=20.0, headers=self.headers, verify=False) as client:
            res = client.post(url, json=payload)
            res.raise_for_status()
            return res.json()["id"]