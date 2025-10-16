from pywebio import start_server, input, output
import requests
from bs4 import BeautifulSoup
import json
import os
import random

put_text = output.put_text
put_success = output.put_success
put_error = output.put_error
put_html = output.put_html

JSON_FILE = "scholar_full_data.json"

# 🧩 قائمة وكلاء (Proxies) مجانية لتجاوز 403
PROXIES = [
    "https://api.allorigins.win/raw?url=",
    "https://corsproxy.io/?",
    "https://thingproxy.freeboard.io/fetch/"
]

def fetch_full_scholar_data():
    url = input.input("أدخل رابط الباحث في Google Scholar:", type="text")
    if not url:
        put_error("❌ يرجى إدخال رابط الباحث")
        return

    try:
        proxy_prefix = random.choice(PROXIES)
        full_url = proxy_prefix + url

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0 Safari/537.36"
        }

        res = requests.get(full_url, headers=headers, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # --- الاسم والصورة ---
        name_tag = soup.find("div", id="gsc_prf_in")
        name = name_tag.text.strip() if name_tag else "غير معروف"
        image_tag = soup.find("img", id="gsc_prf_pup-img")
        image_url = f"https://scholar.google.com{image_tag['src']}" if image_tag else None

        # --- المؤسسة والمجالات ---
        affiliation = soup.find("div", class_="gsc_prf_il")
        affiliation = affiliation.text.strip() if affiliation else "غير محدد"
        fields = [a.text for a in soup.select("#gsc_prf_int a")]
        email_tag = soup.find("div", class_="gsc_prf_ivh")
        email = email_tag.text.strip() if email_tag else "غير متوفر"

        # --- الإحصائيات ---
        stats_table = soup.find("table", id="gsc_rsb_st")
        citations_all = h_index_all = i10_index_all = "0"
        citations_since = h_index_since = i10_index_since = "0"

        if stats_table:
            tds = stats_table.find_all("td", class_="gsc_rsb_std")
            if len(tds) >= 6:
                citations_all = tds[0].text
                citations_since = tds[1].text
                h_index_all = tds[2].text
                h_index_since = tds[3].text
                i10_index_all = tds[4].text
                i10_index_since = tds[5].text

        # --- أول 10 بحوث فقط ---
        publications = []
        for row in soup.select(".gsc_a_tr")[:10]:
            title_tag = row.select_one(".gsc_a_at")
            title = title_tag.text.strip() if title_tag else "بدون عنوان"
            link = f"https://scholar.google.com{title_tag['href']}" if title_tag else "#"

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

        data = {
            "name": name,
            "affiliation": affiliation,
            "fields": fields,
            "email": email,
            "image": image_url,
            "citations": {"all": citations_all, "since2018": citations_since},
            "h_index": {"all": h_index_all, "since2018": h_index_since},
            "i10_index": {"all": i10_index_all, "since2018": i10_index_since},
            "publications": publications,
            "url": url
        }

        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        put_success("✅ تم جلب بيانات الباحث بنجاح!")

        # --- عرض النتائج ---
        html_card = f"""
        <div style='display:flex; align-items:center; gap:20px; margin-bottom:20px;'>
            <img src='{image_url}' width='120' style='border-radius:10px;'/>
            <div>
                <h2>{name}</h2>
                <p><b>المؤسسة:</b> {affiliation}</p>
                <p><b>البريد:</b> {email}</p>
                <p><b>المجالات:</b> {', '.join(fields) if fields else 'غير محدد'}</p>
            </div>
        </div>
        """
        put_html(html_card)

        stats_html = f"""
        <table border='1' cellpadding='8' style='border-collapse:collapse; margin-bottom:20px;'>
            <tr style='background:#f0f0f0'><th>الإحصائية</th><th>الكل</th><th>منذ 2018</th></tr>
            <tr><td>الاستشهادات</td><td>{citations_all}</td><td>{citations_since}</td></tr>
            <tr><td>h-index</td><td>{h_index_all}</td><td>{h_index_since}</td></tr>
            <tr><td>i10-index</td><td>{i10_index_all}</td><td>{i10_index_since}</td></tr>
        </table>
        """
        put_html(stats_html)

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
    port = int(os.environ.get("PORT", 8080))
    start_server(fetch_full_scholar_data, port=port, host="0.0.0.0")
