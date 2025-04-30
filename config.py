import os

from pathlib import Path
print("📄 Aktif config.py burası:", __file__)
BASE_DIR = Path(r"/home/yagizberkuyar/Desktop/Code/Projects/VeritasNews/Scraper")
my_key_gemini = "AIzaSyAINJxJPqnFGg6UCvN3nUoUfI3kFRTSOL8"

# Define subdirectories using pathlib
PULLED_ARTICLES_SAVE_DIR = BASE_DIR / "pulled_articles"
MATCHING_PULL_DIR = BASE_DIR / "article_match_samples" / "s1"
GROUPED_ARTICLES_PULL_DIR = BASE_DIR / "grouped_articles"
GROUPED_ARTICLES_DIR = BASE_DIR / "grouped_articles_updated"
GENERATED_ARTICLES_SAVE_DIR = BASE_DIR / "generated_articles"
SUMMARIZED_GENERATED_ARTICLES_SAVE_DIR = BASE_DIR / "generated_articles"
MATCH_V2_DIR = BASE_DIR / "matched_v2"
PULLED_ARTICLES_SAVE_DIR = BASE_DIR / "pulled_articles"

NEW_ARTICLES_LOG_DIR = BASE_DIR / "new_articles_log.txt"
LOG_DIR = BASE_DIR / "scraper_log.txt"
CACHE_FILE = BASE_DIR / "embedding_cache.json"

OBJECTIVE_ARTICLES_DIR = BASE_DIR / "objectified_jsons"
IMAGE_DIR = BASE_DIR / "images"
IMAGED_JSON_DIR = BASE_DIR / "articles_with_images"

CREATED_ARTICLES = BASE_DIR / "created_articles"
GENERATED_ARTICLES_ARTICLES_V2 = BASE_DIR / "generated_articles"

fixed_prompt_generate_article = """Bütün bu haber makalelerin (JSON) içeriklerine dayanarak nesnel bir makale sağla,
sadece salt bilgileri ver, ayrıca makale için kısa bir başlık sun:"""

fixed_prompt_match_article = """Analyze the following articles which are in JSON format (title, content, genre etc.) 
and group them based on their "content". Output the group numbers for each article. Notice: 
some articles may not match with any other, in that they do not belong to any group. 
Also some of the JSON files may not be proper newspaper articles (due to scraping errors). 
In your response please DO NOT return all the content back as an output. Instead group them by indices 
starting from index 0 (indicies are respect to the given order). Match the news if they reffer to almost same event
(simply being in same context/genre is) not enough. Explain (very shortly) your reasoning of grouping, MAKE SURE THE LAST LINE is
group-article indicies pairs as the following example THIS IS A MUST FOR ME TO PARSE YOUR ANSWER:
"group 0: [...], group 1: [...], ..."
Make sure indicies are 0 based (both for groups and articles) so that I can use them as array indicies in my program. Do not output ungrouped articles.
Here are the articles: """ 

SOURCE_URLS = {
    "nefes": "https://www.nefes.com.tr/", # ÇÖZÜLDÜ
    # "haber_sol": "https://haber.sol.org.tr/", #CLOUDFLARE KORUMASI VAR, BLOCK YİYORUZ, RSS de denendi olmadı
    "diken": "https://www.diken.com.tr/",
    #"gazete_duvar": "https://www.gazeteduvar.com.tr/", # Cloudflare koruması var, block yiyoruz, RSS de denendi olmadı
    "evrensel": "https://www.evrensel.net/",
    "sozcu": "https://www.sozcu.com.tr/", # ÇÖZÜLDÜ RSS ile güncel 50 haber çekiliyor, aynı haberler çekilmiyor
    #yeni sol
    "sendika": "https://www.sendika.org/",
    "gercek_gundem": "https://www.gercekgundem.com/",
    "tele1": "https://tele1.com.tr/",
    "artigercek":"https://artigercek.com/",
    "politikyol": "https://www.politikyol.com/",
    "halktv": "https://www.halktv.com.tr/",

    "trt_haber": "https://www.trthaber.com/ ", #eklendi
    "milliyet": "https://www.milliyet.com.tr/",
    "hurriyet": "https://www.hurriyet.com.tr/",
    "cumhuriyet": "https://www.cumhuriyet.com.tr/",
    "ntv": "https://www.ntv.com.tr/",
    "ahaber": "https://www.ahaber.com.tr/",
    "cnnturk": "https://www.cnnturk.com/",
    "sabah": "https://www.sabah.com.tr/",
    
    "haberturk": "https://www.haberturk.com/",
    "ensonhaber": "https://www.ensonhaber.com/",
    "posta": "https://www.posta.com.tr/",
    "takvim": "https://www.takvim.com.tr/",
    "yeni_safak": "https://www.yenisafak.com/",#çözüldü 
    "star": "https://www.star.com.tr/",
    "turkiye_gazetesi": "https://www.turkiyegazetesi.com.tr/",
    "dunya": "https://www.dunya.com/",
    "birgun": "https://www.birgun.net/",
    "t24": "https://t24.com.tr/",
    "bianet": "https://bianet.org/",
    "hurriyet_daily_news": "https://www.hurriyetdailynews.com/",
    "daily_sabah": "https://www.dailysabah.com/",
    # Add additional sources as needed
}

URL_FIELDS = ["/haberi/","/haber/", "/news/", "/gundem/", "/spor/", "/yasam/", "/dunya/", "/turkiye/", "/ekonomi/",
               "/teknoloji/", "/siyaset/", "/sondakika/", "/son-dakika/", "/son_dakika/", "/son-24-saat/", "/daily/","/kategori/1/",
               "/kategori/2/","/kategori/3/","/kategori/4/","/kategori/5/","/kategori/6/","/kategori/7/","/yazi/","/2024/","/2025/", "-p"
               "/sondakika-haberleri/"] #haberi eklendi

EXCLUDED_URL_KEYWORDS = ["/galeri/", "/foto/", "/foto-haber/", "/video/", "/video-haber/", "/foto_haber/",
                          "/video_haber/", "/fotohaber/", "/videohaber/", "/cdn-cgi/", "/email-protection/"] # /cdn-cgi/ ve /email-protection eklendi

SERPAPI_API_KEY = "787779d443ef32619f473975017aaa88f92b6cc36838eef43e944490f55a8160"