"""Download the public-domain paintings of the Họa. catalogue from Wikimedia Commons.

Writes demo/web/img/<productId>.jpg, demo/web/img/credits.json (image credits for the UI),
demo/web/img/rooms/ (sample rooms + rooms.json), demo/data/catalog.json, demo/data/ATTRIBUTION.md and
the alternative versions used as image queries in the evaluation (demo/data/eval_images/).
Only files whose Commons licence is "Public domain" are accepted.

Usage: python3 tools/fetch_paintings.py [--force]
"""
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"
IMG = DEMO / "web" / "img"
DATA = DEMO / "data"
EVAL = DATA / "eval_images"
API = "https://commons.wikimedia.org/w/api.php"
UA = "PTIT-student-demo/1.0 (https://github.com/scalliontor) python-urllib"

ARTISTS = {
    "A01": ("Claude Monet", "French", "1840–1926"),
    "A02": ("Vincent van Gogh", "Dutch", "1853–1890"),
    "A03": ("Katsushika Hokusai", "Japanese", "1760–1849"),
    "A04": ("Utagawa Hiroshige", "Japanese", "1797–1858"),
    "A05": ("Gustav Klimt", "Austrian", "1862–1918"),
    "A06": ("Georges Seurat", "French", "1859–1891"),
    "A07": ("Pierre-Auguste Renoir", "French", "1841–1919"),
    "A08": ("Johannes Vermeer", "Dutch", "1632–1675"),
    "A09": ("J. M. W. Turner", "British", "1775–1851"),
    "A10": ("Caspar David Friedrich", "German", "1774–1840"),
    "A11": ("Paul Cézanne", "French", "1839–1906"),
    "A12": ("Paul Gauguin", "French", "1848–1903"),
    "A13": ("Edvard Munch", "Norwegian", "1863–1944"),
    "A14": ("Wassily Kandinsky", "Russian", "1866–1944"),
    "A15": ("Édouard Manet", "French", "1832–1883"),
    "A16": ("Edgar Degas", "French", "1834–1917"),
    "A17": ("Camille Pissarro", "French", "1830–1903"),
    "A18": ("Mary Cassatt", "American", "1844–1926"),
    "A19": ("Henri Rousseau", "French", "1844–1910"),
}

# (productId, artistId, title, year, style, subject, colour, print medium, width cm, height cm, price USD, stock,
#  Commons search query, words that must appear in the file title)
PAINTINGS = [
    ("P01", "A01", "Impression, Sunrise", 1872, "Impressionism", "seascape", "blue", "Fine art paper", 60, 46, 79, 6,
     "Monet Impression Sunrise", ["monet", "impression"]),
    ("P02", "A01", "Water Lilies", 1906, "Impressionism", "flowers", "green", "Canvas print", 60, 56, 69, 8,
     "Claude Monet Water Lilies 1906 Ryerson", ["water", "lil"]),
    ("P03", "A01", "Woman with a Parasol", 1875, "Impressionism", "landscape", "blue", "Canvas print", 50, 61, 89, 5,
     "Claude Monet Woman with a Parasol Madame Monet and Her Son", ["parasol"]),
    ("P04", "A01", "Poppy Field", 1873, "Impressionism", "landscape", "green", "Canvas print", 65, 50, 119, 4,
     "Claude Monet Poppy Field Argenteuil 1873", ["monet", "pop"]),
    ("P05", "A02", "The Starry Night", 1889, "Post-Impressionism", "landscape", "blue", "Canvas print", 92, 74, 129, 7,
     "Van Gogh Starry Night Google Art Project", ["file:van_gogh_-_starry_night"]),  # MoMA 1889, not the Rhône
    ("P06", "A02", "Sunflowers", 1888, "Post-Impressionism", "flowers", "yellow", "Canvas print", 56, 72, 119, 6,
     "Vincent van Gogh Sunflowers VGM F458", ["sunflowers"]),
    ("P07", "A02", "Café Terrace at Night", 1888, "Post-Impressionism", "cityscape", "yellow", "Canvas print", 52, 66,
     109, 5, "Van Gogh Cafe Terrace at Night Kroller-Muller", ["terrace"]),
    ("P08", "A02", "Wheat Field with Cypresses", 1889, "Post-Impressionism", "landscape", "yellow", "Canvas print",
     70, 56, 95, 6, "Vincent van Gogh Wheat Field with Cypresses National Gallery", ["cypress"]),
    ("P09", "A02", "Irises", 1889, "Post-Impressionism", "flowers", "purple", "Fine art paper", 60, 47, 89, 6,
     "Irises Vincent van Gogh 1889 Getty", ["irises"]),
    ("P10", "A03", "The Great Wave off Kanagawa", 1831, "Ukiyo-e", "seascape", "blue", "Fine art paper", 60, 40, 75, 10,
     "Tsunami by Hokusai 19th century", ["hokusai"]),
    ("P11", "A03", "Fine Wind, Clear Morning (Red Fuji)", 1831, "Ukiyo-e", "landscape", "red", "Fine art paper", 60, 40,
     65, 8, "Red Fuji southern wind clear morning Hokusai", ["fuji"]),
    ("P12", "A04", "Sudden Shower over Shin-Ōhashi Bridge", 1857, "Ukiyo-e", "cityscape", "blue", "Fine art paper",
     40, 60, 59, 7, "Hiroshige Sudden Shower over Shin-Ohashi bridge", ["shower"]),
    ("P13", "A04", "Plum Park in Kameido", 1857, "Ukiyo-e", "flowers", "red", "Fine art paper", 40, 60, 62, 7,
     "Hiroshige Plum Park in Kameido", ["plum"]),
    ("P14", "A05", "The Kiss", 1908, "Art Nouveau", "portrait", "yellow", "Canvas print", 60, 60, 159, 4,
     "Gustav Klimt Der Kuss Liebespaar Belvedere", ["kuss"]),
    ("P15", "A05", "Portrait of Adele Bloch-Bauer I", 1907, "Art Nouveau", "portrait", "yellow", "Canvas print", 60, 60,
     180, 3, "Gustav Klimt Portrait of Adele Bloch-Bauer I", ["adele"]),
    ("P16", "A06", "A Sunday on La Grande Jatte", 1884, "Post-Impressionism", "everyday life", "green", "Canvas print",
     90, 60, 149, 4, "Georges Seurat A Sunday on La Grande Jatte 1884", ["jatte"]),
    ("P17", "A07", "Bal du moulin de la Galette", 1876, "Impressionism", "everyday life", "blue", "Canvas print", 80, 60,
     139, 4, "Renoir Bal du moulin de la Galette Musee d'Orsay", ["galette"]),
    ("P18", "A08", "Girl with a Pearl Earring", 1665, "Baroque", "portrait", "black", "Canvas print", 40, 46, 145, 5,
     "Meisje met de parel Vermeer", ["vermeer"]),
    ("P19", "A08", "The Milkmaid", 1658, "Baroque", "everyday life", "yellow", "Canvas print", 41, 46, 125, 4,
     "Johannes Vermeer Het melkmeisje", ["melk"]),
    ("P20", "A09", "The Fighting Temeraire", 1839, "Romanticism", "seascape", "orange", "Canvas print", 80, 60, 119, 5,
     "The Fighting Temeraire tugged to her last berth Turner", ["temeraire"]),
    ("P21", "A10", "Wanderer above the Sea of Fog", 1818, "Romanticism", "landscape", "blue", "Canvas print", 50, 64,
     109, 6, "Caspar David Friedrich Wanderer above the sea of fog", ["wanderer"]),
    ("P22", "A11", "Mont Sainte-Victoire", 1904, "Post-Impressionism", "landscape", "green", "Canvas print", 70, 56, 95,
     5, "Paul Cezanne Mont Sainte-Victoire 1904 Philadelphia", ["victoire"]),
    ("P23", "A11", "The Basket of Apples", 1893, "Post-Impressionism", "still life", "brown", "Canvas print", 60, 48, 85,
     6, "Paul Cezanne The Basket of Apples Art Institute", ["apples"]),
    ("P24", "A12", "Tahitian Women on the Beach", 1891, "Post-Impressionism", "portrait", "orange", "Canvas print", 70,
     52, 115, 4, "Gauguin Tahitian Women on the Beach 1891", ["gauguin_056.jpg"]),
    ("P25", "A13", "The Scream", 1893, "Expressionism", "portrait", "orange", "Fine art paper", 46, 58, 155, 5,
     "Edvard Munch 1893 The Scream oil tempera and pastel on cardboard", ["scream"]),
    ("P26", "A14", "Composition VII", 1913, "Abstract", "abstract", "red", "Canvas print", 90, 60, 139, 3,
     "Vassily Kandinsky 1913 Composition 7", ["kandinsky"]),
    ("P27", "A15", "A Bar at the Folies-Bergère", 1882, "Realism", "portrait", "black", "Canvas print", 70, 52, 129, 4,
     "Edouard Manet A Bar at the Folies-Bergere", ["bergère", "bergere", "folies"]),
    ("P28", "A16", "The Dance Foyer at the Opera", 1872, "Impressionism", "everyday life", "brown", "Canvas print", 60,
     48, 99, 5, "Edgar Degas The Dance Class Musee d'Orsay", ["dance"]),
    ("P29", "A17", "Boulevard Montmartre, Spring", 1897, "Impressionism", "cityscape", "green", "Canvas print", 65, 52,
     85, 6, "Camille Pissarro Boulevard Montmartre Spring", ["montmartre"]),
    ("P30", "A18", "The Child's Bath", 1893, "Impressionism", "portrait", "pink", "Fine art paper", 46, 60, 79, 6,
     "Mary Cassatt The Child's Bath Art Institute", ["bath"]),
    ("P31", "A19", "Tiger in a Tropical Storm (Surprised!)", 1891, "Naive art", "landscape", "green", "Canvas print",
     65, 52, 105, 5, "Henri Rousseau Tiger in a Tropical Storm", ["rousseau", "tiger", "surprised"]),
    ("P32", "A01", "The Japanese Footbridge", 1899, "Impressionism", "landscape", "green", "Canvas print", 60, 56, 109,
     5, "Claude Monet The Japanese Footbridge National Gallery of Art 1899", ["footbridge", "bridge"]),
]

FRAMES = [  # (productId, name, material, colour, size, price USD, stock)
    ("F01", "Natural oak frame 40 x 60", "oak", "brown", "40 x 60 cm", 45, 20),
    ("F02", "Walnut frame 50 x 70", "walnut", "brown", "50 x 70 cm", 65, 15),
    ("F03", "Matte black aluminium frame 40 x 60", "aluminium", "black", "40 x 60 cm", 35, 25),
    ("F04", "Antique gold frame 60 x 90", "gilded wood", "yellow", "60 x 90 cm", 90, 8),
    ("F05", "Matte white frame 30 x 40", "painted pine", "white", "30 x 40 cm", 25, 30),
]

# Sample rooms of "Try it in your room" (UC14): CC0 photos from Unsplash mirrored on Commons.
ROOMS = [  # (id, label, Commons file, wall box [x, y, w, h] in 0..1 where the painting is hung)
    ("room1", "Bright living room, pale blue sofa", "At Home (Unsplash).jpg", [0.30, 0.10, 0.40, 0.42]),
    ("room2", "Brick-wall apartment, warm tones", "Budapest Apartment (Unsplash).jpg", [0.50, 0.10, 0.30, 0.42]),
    ("room3", "Living room in afternoon light", "Afternoon light (Unsplash).jpg", [0.40, 0.08, 0.45, 0.38]),
]

# Image queries for the evaluation: another version or reproduction of a catalogue painting.
# (evalId, expected productId, Commons query, words that must appear, words that must not appear)
EVAL_IMAGES = [
    ("Q01", "P06", "Van Gogh Sunflowers Neue Pinakothek Munich", ["sunflower"], []),
    ("Q02", "P10", "Great Wave off Kanagawa Metropolitan Museum Hokusai", ["wave"], ["tsunami_by_hokusai_19th_century"]),
    ("Q03", "P22", "Cezanne Mont Sainte-Victoire Kunsthaus Zurich", ["victoire"], []),
    ("Q04", "P02", "Monet Water Lilies 1916 National Museum of Western Art", ["water", "lil"], ["ryerson"]),
    ("Q05", "P05", "Van Gogh Starry Night Museum of Modern Art photograph", ["starry"], ["google_art_project"]),
    ("Q06", "P14", "The Kiss Gustav Klimt Google Cultural Institute", ["kiss", "kuss"], []),
    ("Q07", "P25", "Edvard Munch The Scream 1910 tempera Munch Museum", ["scream", "skrik"], []),
    ("Q08", "P18", "Girl with a Pearl Earring Mauritshuis Vermeer", ["pearl", "parel"], []),
]


def get_json(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def download(url, target):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as response:
        target.write_bytes(response.read())


def strip_html(text):
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def search(query, must, must_not=(), skip_titles=()):
    """First public-domain JPEG/PNG file on Commons matching the query and the title filters."""
    data = get_json({
        "action": "query", "format": "json", "generator": "search", "gsrsearch": query + " filetype:bitmap",
        "gsrnamespace": 6, "gsrlimit": 15, "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 960,
    })
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    for page in pages:
        title = page["title"]
        key = title.lower().replace(" ", "_")
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        licence = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
        if title in skip_titles or info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if not any(w in key for w in must) or any(w in key for w in must_not):
            continue
        if "public domain" not in licence.lower() or info.get("width", 0) < 600:
            continue
        return {
            "file": title, "thumb": info["thumburl"], "page": info.get("descriptionurl"),
            "licence": licence, "credit": strip_html(meta.get("Artist", {}).get("value", ""))[:120],
        }
    return None


def fetch_rooms():
    """Download the sample room photos; only CC0 or public-domain files are accepted."""
    rooms = []
    (IMG / "rooms").mkdir(parents=True, exist_ok=True)
    for room_id, label, file_name, wall_box in ROOMS:
        data = get_json({"action": "query", "format": "json", "titles": "File:" + file_name, "prop": "imageinfo",
                         "iiprop": "url|extmetadata", "iiurlwidth": 1600})
        info = next(iter(data["query"]["pages"].values()))["imageinfo"][0]
        licence = strip_html(info["extmetadata"].get("LicenseShortName", {}).get("value", ""))
        if "cc0" not in licence.lower() and "public domain" not in licence.lower():
            raise SystemExit(f"{file_name} is not CC0/public domain: {licence}")
        target = IMG / "rooms" / f"{room_id}.jpg"
        if not target.exists():
            download(info["thumburl"], target)
            time.sleep(0.4)
        rooms.append({"roomId": room_id, "label": label, "imageUrl": f"/img/rooms/{room_id}.jpg", "wallBox": wall_box,
                      "source": {"file": "File:" + file_name, "page": info.get("descriptionurl"), "licence": licence}})
    return rooms


def main():
    force = "--force" in sys.argv
    IMG.mkdir(parents=True, exist_ok=True)
    EVAL.mkdir(parents=True, exist_ok=True)
    old = {}
    if (DATA / "catalog.json").exists():
        old = {p["productId"]: p for p in json.loads((DATA / "catalog.json").read_text())["paintings"]}
    paintings, used = [], set()
    for (pid, aid, title, year, style, subject, color, medium, w, h, price, stock, query, must) in PAINTINGS:
        target = IMG / f"{pid}.jpg"
        source = old.get(pid, {}).get("source") if not force else None
        if not (source and target.exists()):
            source = search(query, must)
            if source is None:
                print(f"skip {pid} {title}: no public-domain file found")
                continue
            download(source["thumb"], target)
            time.sleep(0.4)
        used.add(source["file"])
        artist = ARTISTS[aid]
        paintings.append({
            "productId": pid, "artistId": aid, "name": title, "artist": artist[0], "yearCreated": year,
            "style": style, "subject": subject, "dominantColor": color, "medium": medium, "widthCm": w,
            "heightCm": h, "price": price, "stockQuantity": stock, "imageUrl": f"/img/{pid}.jpg",
            "description": f"Museum-quality {medium.lower()} of the {year} original by {artist[0]}.",
            "source": source,
        })
        print(f"ok {pid} {title} <- {source['file']}")
    evals = []
    old_evals = {}
    if (DATA / "eval_images.json").exists():
        old_evals = {e["queryId"]: e for e in json.loads((DATA / "eval_images.json").read_text())}
    for qid, expected, query, must, must_not in EVAL_IMAGES:
        target = EVAL / f"{qid}.jpg"
        reuse = not force and target.exists() and qid in old_evals
        found = old_evals[qid]["source"] if reuse else search(query, must, must_not, skip_titles=used)
        if found is None:
            print(f"skip eval {qid}: nothing found")
            continue
        if force or not target.exists():
            download(found["thumb"], target)
            time.sleep(0.4)
        evals.append({"queryId": qid, "expected": expected, "image": f"data/eval_images/{qid}.jpg", "source": found})
        print(f"eval {qid} -> {expected} <- {found['file']}")
    rooms = fetch_rooms()
    (IMG / "rooms" / "rooms.json").write_text(json.dumps(rooms, ensure_ascii=False, indent=2))
    credits = {p["productId"]: {"credit": p["source"]["credit"], "licence": p["source"]["licence"],
                                "page": p["source"]["page"]} for p in paintings}
    (IMG / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2))
    artists = [{"artistId": k, "name": v[0], "nationality": v[1], "lifeYears": v[2]} for k, v in ARTISTS.items()]
    frames = [{"productId": f[0], "name": f[1], "material": f[2], "color": f[3], "sizeLabel": f[4], "price": f[5],
               "stockQuantity": f[6], "imageUrl": None,
               "description": f"{f[1]} in {f[2]}, anti-glare glass and hanging kit included."}
              for f in FRAMES]
    (DATA / "catalog.json").write_text(json.dumps(
        {"artists": artists, "paintings": paintings, "frames": frames}, ensure_ascii=False, indent=2))
    (DATA / "eval_images.json").write_text(json.dumps(evals, ensure_ascii=False, indent=2))
    lines = ["# Image sources", "",
             "Painting images come from Wikimedia Commons; only files licensed **Public domain** are used (the",
             "works are out of copyright). Họa. is the demo shop of the essay; the images illustrate the prints.", "",
             "| Id | Work | Artist | Commons file | Licence |", "|---|---|---|---|---|"]
    for p in paintings:
        s = p["source"]
        lines.append(f"| {p['productId']} | {p['name']} ({p['yearCreated']}) | {p['artist']} | "
                     f"[{s['file']}]({s['page']}) | {s['licence']} |")
    lines += ["", "## Query images of the evaluation", "", "| Id | Expected product | Commons file | Licence |",
              "|---|---|---|---|"]
    lines += [f"| {e['queryId']} | {e['expected']} | [{e['source']['file']}]({e['source']['page']}) | "
              f"{e['source']['licence']} |" for e in evals]
    lines += ["", "## Sample rooms of \"Try it in your room\"", "", "| Id | Room | Commons file | Licence |",
              "|---|---|---|---|"]
    lines += [f"| {r['roomId']} | {r['label']} | [{r['source']['file']}]({r['source']['page']}) | "
              f"{r['source']['licence']} |" for r in rooms]
    (DATA / "ATTRIBUTION.md").write_text("\n".join(lines) + "\n")
    print(f"{len(paintings)} paintings, {len(frames)} frames, {len(evals)} evaluation images")


if __name__ == "__main__":
    main()
