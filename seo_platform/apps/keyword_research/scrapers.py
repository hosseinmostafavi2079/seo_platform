# apps/keyword_research/scrapers.py
import re
import httpx

class CompetitorScraper:
    @staticmethod
    def scrape_headings(urls: list) -> str:
        """آماده‌سازی خلاصه‌ای از تگ‌های هدینگ رقبا برای ارسال به عنوان کانتکست به AI"""
        context_data = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        for url in urls:
            if not url:
                continue
            try:
                with httpx.Client(timeout=10.0, headers=headers, follow_redirects=True) as client:
                    res = client.get(url)
                    if res.status_code == 200:
                        html = res.text
                        # استخراج تگ‌های H1 و H2 با Regex به جای BeautifulSoup برای سرعت بالا و پایداری کانتینر
                        h1s = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
                        h2s = re.findall(r'<h2[^>]*>(.*?)</h2>', html, re.IGNORECASE | re.DOTALL)
                        
                        clean_h1s = [re.sub(r'<[^>]+>', '', h).strip() for h in h1s if h.strip()]
                        clean_h2s = [re.sub(r'<[^>]+>', '', h).strip() for h in h2s if h.strip()]
                        
                        context_data.append(f"URL: {url}\nH1 Headings: {', '.join(clean_h1s)}\nH2 Headings: {', '.join(clean_h2s)}\n")
            except Exception as e:
                context_data.append(f"URL: {url} (Failed to scrape: {str(e)})\n")
                
        return "\n".join(context_data)