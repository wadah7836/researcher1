# scholar_app.py
from pywebio import start_server, input, output
import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
import random
import time
from datetime import datetime

put_text = output.put_text
put_success = output.put_success
put_error = output.put_error
put_html = output.put_html

LOG_FILE = "scholar_log.txt"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.70 Safari/537.36",
]

def log_error(message):
    """تسجيل أي خطأ في ملف لسهولة التتبع"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] {message}\n")

def extract_author_id(scholar_url: str):
    if not scholar_url:
        return None
    parsed = urllib.parse.urlparse(scholar_url)
    q = urllib.parse.parse_qs(parsed.query)
    if "user" in q and q["user"]:
        return q["user"][0]
    if "user=" in scholar_url:
        try:
            part = scholar_url.split("user=")[1].split("&")[0]
            return part
        except Exception:
            return None
    return None

def fetch_via_requests(url: str, retries=3, delay=5):
    """يحاول جلب الصفحة مع إعادة المحاولة وتبديل User-Agent"""
    for attempt in range(1, retries + 1):
        try:
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.text
            else:
                log_error(f"HTTP {resp.status_code} أثناء محاولة {attempt}")
        except Exception as e:
            log_error(f"خطأ أثناء الجلب في المحاولة {attempt}: {e}")
        time.sleep(delay)
    raise Exception("فشل الاتصال بعد عدة محاولات. قد يكون Google حظرك مؤقتًا.")

def parse_publications(soup):
    """تحليل البحوث من صفحة واحدة"""
    publications = []
    for row in soup.select(".gsc_a_tr"):
        title_tag = row.select_one(".gsc_a_at")
        title = title_tag.text.strip() if title_tag else "بدون عنوان"
        link = "https://scholar.google.com" + title_tag["href"] if title_tag else "#"
        authors_tag = row.select_one(".gsc_a_at+ .gs_gray")
        authors = authors_tag.text.strip() if authors_tag else ""
        journal_tag = row.select(".gs_gray")
        journal = journal_tag[1].text.strip() if len(journal_tag) > 1 else ""
        cited_tag = row.select_one(".gsc_a_c a")
        citations = cited_tag.text.strip() if cited_tag else "0"
        year_tag = row.select_one(".gsc_a_y span")
        year = year_tag.text.strip() if year_tag else "—"
        publications.append({
            "title": title,
            "authors": authors,
            "journal": journal,
            "citations": citations,
            "year": year,
            "link": link
        })
    return publications

def parse_soup_to_data(soup, base_url):
    """تحليل بيانات الباحث وجلب كل البحوث"""
    name_tag = soup.find("div", id="gsc_prf_in")
    name = name_tag.text.strip() if name_tag else "غير معروف"
    image_tag = soup.find("img", id="gsc_prf_pup-img")
    image_url = "https://scholar.google.com" + image_tag["src"] if image_tag else None

    affiliation = soup.find("div", class_="gsc_prf_il")
    affiliation = affiliation.text.strip() if affiliation else "غير محدد"
    fields = [a.text.strip() for a in soup.select("#gsc_prf_int a")]
    email_tag = soup.find("div", class_="gsc_prf_ivh")
    email = email_tag.text.strip() if email_tag else "غير متوفر"

    citations_all = h_index_all = i10_index_all = "0"
    stats_table = soup.find("table", id="gsc_rsb_st")
    if stats_table:
        tds = stats_table.find_all("td", class_="gsc_rsb_std")
        if len(tds) >= 6:
            citations_all, _, h_index_all, _, i10_index_all, _ = [td.text for td in tds[:6]]

    # جلب كل البحوث عبر الصفحات
    publications = []
    start = 0
    while True:
        page_url = f"{base_url}&cstart={start}&pagesize=20"
        html = fetch_via_requests(page_url)
        page_soup = BeautifulSoup(html, "html.parser")
        new_pubs = parse_publications(page_soup)
        if not new_pubs:
            break
        publications.extend(new_pubs)
        start += 20
        time.sleep(1)  # تأخير بسيط لتجنب الحظر المؤقت

    return {
        "name": name,
        "affiliation": affiliation,
        "fields": fields,
        "email": email,
        "image": image_url,
        "citations": citations_all,
        "h_index": h_index_all,
        "i10_index": i10_index_all,
        "publications": publications,
    }

def fetch_full_scholar_data():
    # شعار الهيئة في البداية
    put_html("""
        <h1 style='text-align:center; color:#004aad; margin-bottom:20px;'>هيئة البحث العلمي</h1>
        <hr>
    """)

    url = input.input("أدخل رابط الباحث في Google Scholar:", type="text")
    if not url:
        put_error("يرجى إدخال رابط الباحث")
        return

    try:
        put_text("🔍 جاري جلب البيانات من Google Scholar...")
        html = fetch_via_requests(url)
        soup = BeautifulSoup(html, "html.parser")
        data = parse_soup_to_data(soup, url)

        # عرض بيانات الباحث
        html_card = f"""
        <div style='display:flex; align-items:center; gap:20px; margin-bottom:20px; margin-top:20px;'>
            <img src='{data.get('image')}' alt='صورة الباحث' width='120' style='border-radius:10px;'/>
            <div>
                <h2>{data.get('name')}</h2>
                <p><b>المؤسسة:</b> {data.get('affiliation')}</p>
                <p><b>البريد:</b> {data.get('email')}</p>
                <p><b>المجالات:</b> {', '.join(data.get('fields') or []) if data.get('fields') else 'غير محدد'}</p>
            </div>
        </div>
        """
        put_html(html_card)

        stats_html = f"""
        <table border='1' cellpadding='8' style='border-collapse:collapse; margin-bottom:20px;'>
            <tr style='background:#f0f0f0'><th>الإحصائية</th><th>القيمة</th></tr>
            <tr><td>الاستشهادات</td><td>{data['citations']}</td></tr>
            <tr><td>h-index</td><td>{data['h_index']}</td></tr>
            <tr><td>i10-index</td><td>{data['i10_index']}</td></tr>
        </table>
        """
        put_html(stats_html)

        pubs = data.get("publications", [])
        total_pubs = len(pubs)
        put_html(f"<h3 style='color:#004aad;'>عدد البحوث الكلي: {total_pubs}</h3>")

        pubs_html = """
        <table border='1' cellpadding='6' style='border-collapse:collapse; width:100%'>
            <tr style='background:#f0f0f0'>
                <th>العنوان</th><th>المؤلفون</th><th>المجلة</th><th>الاستشهادات</th><th>السنة</th>
            </tr>
        """
        for p in pubs:
            pubs_html += f"""
            <tr>
                <td><a href='{p['link']}' target='_blank'>{p['title']}</a></td>
                <td>{p['authors']}</td>
                <td>{p['journal']}</td>
                <td>{p['citations']}</td>
                <td>{p['year']}</td>
            </tr>
            """
        pubs_html += "</table>"
        put_html(pubs_html)

        # شعار الهيئة في النهاية
        put_html("""
            <hr>
            <h2 style='text-align:center; color:#004aad; margin-top:20px;'>هيئة البحث العلمي</h2>
        """)

    except Exception as e:
        log_error(f"خطأ أثناء التنفيذ: {e}")
        put_error(f"❌ حدث خطأ أثناء الجلب: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    start_server(fetch_full_scholar_data, port=port, host="0.0.0.0")
