from pywebio import start_server, input, output
from bs4 import BeautifulSoup
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

put_text = output.put_text
put_success = output.put_success
put_error = output.put_error
put_html = output.put_html

JSON_FILE = "scholar_full_data.json"


def get_html_with_selenium(url):
    """يفتح صفحة الباحث عبر متصفح حقيقي (headless) ويعيد HTML."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    driver.get(url)
    time.sleep(5)  # انتظار تحميل الصفحة
    html = driver.page_source
    driver.quit()
    return html


def parse_scholar_page(html):
    """تحليل الصفحة باستخدام BeautifulSoup واستخراج البيانات."""
    soup = BeautifulSoup(html, "html.parser")

    name_tag = soup.find("div", id="gsc_prf_in")
    name = name_tag.text.strip() if name_tag else "غير معروف"

    image_tag = soup.find("img", id="gsc_prf_pup-img")
    image_url = "https://scholar.google.com" + image_tag["src"] if image_tag else None

    affiliation_tag = soup.find("div", class_="gsc_prf_il")
    affiliation = affiliation_tag.text.strip() if affiliation_tag else "غير محدد"

    fields = [a.text for a in soup.select("#gsc_prf_int a")]

    email_tag = soup.find("div", class_="gsc_prf_ivh")
    email = email_tag.text.strip() if email_tag else "غير متوفر"

    citations_all = h_index_all = i10_index_all = "0"
    stats_table = soup.find("table", id="gsc_rsb_st")
    if stats_table:
        tds = stats_table.find_all("td", class_="gsc_rsb_std")
        if len(tds) >= 6:
            citations_all = tds[0].text
            h_index_all = tds[2].text
            i10_index_all = tds[4].text

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

    return {
        "name": name,
        "affiliation": affiliation,
        "fields": fields,
        "email": email,
        "image": image_url,
        "citations": {"all": citations_all},
        "h_index": {"all": h_index_all},
        "i10_index": {"all": i10_index_all},
        "publications": publications,
    }


def fetch_full_scholar_data():
    url = input.input("أدخل رابط الباحث في Google Scholar:", type="text")
    if not url:
        put_error("يرجى إدخال رابط الباحث")
        return

    try:
        put_text("🔍 جاري جلب البيانات من Google Scholar...")
        html = get_html_with_selenium(url)
        data = parse_scholar_page(html)
        data["url"] = url

        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        put_success(f"✅ تم جلب جميع بيانات الباحث وحفظها في {JSON_FILE}")

        html_card = f"""
        <div style='display:flex; align-items:center; gap:20px; margin-bottom:20px;'>
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
            <tr style='background:#f0f0f0'><th>الإحصائية</th><th>الكل</th></tr>
            <tr><td>الاستشهادات</td><td>{data['citations']['all']}</td></tr>
            <tr><td>h-index</td><td>{data['h_index']['all']}</td></tr>
            <tr><td>i10-index</td><td>{data['i10_index']['all']}</td></tr>
        </table>
        """
        put_html(stats_html)

        publications = data.get("publications") or []
        pubs_html = """
        <table border='1' cellpadding='6' style='border-collapse:collapse; width:100%'>
            <tr style='background:#f0f0f0'>
                <th>العنوان</th><th>المؤلفون</th><th>المجلة</th><th>الاستشهادات</th><th>السنة</th>
            </tr>
        """
        for pub in publications:
            pubs_html += f"""
            <tr>
                <td><a href='{pub['link']}' target='_blank'>{pub['title']}</a></td>
                <td>{pub['authors']}</td>
                <td>{pub['journal']}</td>
                <td>{pub['citations']}</td>
                <td>{pub['year']}</td>
            </tr>
            """
        pubs_html += "</table>"
        put_html(pubs_html)

    except Exception as e:
        put_error(f"❌ حدث خطأ أثناء الجلب: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    start_server(fetch_full_scholar_data, port=port, host="0.0.0.0")
