from flask import Flask, render_template, jsonify, request, send_from_directory
import requests
from bs4 import BeautifulSoup
import datetime
import re
import time

app = Flask(__name__)

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

DAILY_URL = "https://www.pib.gov.in/allRel.aspx?reg=3&lang=1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

UPSC_KEYWORDS = [
    # Your full keyword list here (use the one you already have)
    "parliament", "supreme court", "election", "constitution", "bill", "act",
    "president", "governor", "amendment", "fundamental rights", "dpsp",
    "judiciary", "tribunal", "federalism", "local government", "panchayati raj",
    "prime minister", "cabinet", "approves", "launch", "scheme",
    "gdp", "inflation", "budget", "fiscal", "rbi", "monetary policy", "exports",
    "import", "msme", "startup", "unemployment", "poverty", "economic survey",
    "banking", "insurance", "tax", "gst", "disinvestment",
    "climate change", "biodiversity", "pollution", "conservation", "wildlife",
    "forest", "river", "monsoon", "earthquake", "disaster", "renewable energy",
    "wetland", "ramsar", "carbon", "paris agreement",
    "isro", "nasa", "satellite", "mission", "ai ", "artificial intelligence",
    "5g", "digital india", "cyber", "biotech", "vaccine", "health", "disease",
    "united nations", "who", "imf", "world bank", "g20", "bilateral", "summit",
    "neighbourhood", "saarc", "bimstec", "foreign policy", "diaspora",
    "caste", "gender", "tribe", "education", "migration", "urban",
    "rural", "inequality", "social justice", "empowerment",
    "committee", "commission", "report", "index", "portal", "yojana"
]

def clean_text(text):
    return re.sub(r'\s+', ' ', re.sub(r'<.*?>', '', text)).strip()

def extract_smart_summary(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")
        div = None
        for sel in ["div#Releseases", "div.press-content", "div.content-area", "div.col-xs-12"]:
            div = soup.select_one(sel)
            if div:
                break
        if not div:
            div = soup.body
        for tag in div(["script", "style"]):
            tag.decompose()
        text = clean_text(div.get_text())

        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.split()) > 5]

        if not sentences:
            return "Summary not available."

        scored = []
        for i, sent in enumerate(sentences):
            score = sum(1 for kw in UPSC_KEYWORDS if kw in sent.lower())
            if i < 3:
                score += 2
            scored.append((sent, score))

        scored.sort(key=lambda x: (-x[1], sentences.index(x[0])))
        top = scored[:7]
        top.sort(key=lambda x: sentences.index(x[0]))
        summary_sentences = [s[0] for s in top if s[1] > 0]

        if not summary_sentences:
            summary_sentences = sentences[:3]

        return summary_sentences
    except:
        return [f"Could not summarize."]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch')
def fetch():
    try:
        # Get date parameter (dd/mm/yyyy), default to today
        date_str = request.args.get('date', '')
        if not date_str:
            today = datetime.date.today()
            date_str = today.strftime("%d/%m/%Y")
        else:
            # validate format
            try:
                datetime.datetime.strptime(date_str, "%d/%m/%Y")
            except:
                return jsonify({"error": "Invalid date format. Use dd/mm/yyyy"}), 400

        # Build URL with date
        url = f"{DAILY_URL}&date={date_str}"
        print(f"Fetching releases for {date_str}")

        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        releases = []
        for a in soup.find_all("a", href=re.compile(r"PressRelease(Page|Iframe)")):
            title = a.get_text(strip=True)
            link = a["href"]
            if link.startswith("/"):
                link = "https://www.pib.gov.in" + link
            if title and link:
                releases.append({"title": title, "link": link})

        unique = {r["title"]: r for r in releases}.values()
        relevant = [r for r in unique if any(kw in r["title"].lower() for kw in UPSC_KEYWORDS)]

        articles = []
        for i, r in enumerate(relevant):
            print(f"Fetching {i+1}/{len(relevant)}: {r['title'][:60]}")
            summary = extract_smart_summary(r["link"])
            articles.append({
                "title": r["title"],
                "link": r["link"],
                "bullets": summary if isinstance(summary, list) else [summary]
            })
            time.sleep(0.5)

        return jsonify({
            "date": datetime.datetime.strptime(date_str, "%d/%m/%Y").strftime("%d %B %Y"),
            "articles": articles
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run()
