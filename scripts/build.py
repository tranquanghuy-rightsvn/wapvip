#!/usr/bin/env python3
"""Build html/ from data/*.json + templates/*.html.

data/ la nguon chan ly (do GAS CMS ghi), templates/ la design goc (sua tay).
Khong sua tay html/index.html hay html/posts/<slug>/index.html - build lai se mat.
Chay: python3 scripts/build.py
"""
import html
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TEMPLATES = ROOT / "templates"
SITE_DIR = ROOT / "html"

MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100MB — khop rule cua CMS (xem gas.md muc 3)
NAME_CLASSES = ["c1", "c2", "c3", "c4", "c5"]  # mau cycle, tai su dung tu style.css hien co
HDR_CLASSES = ["teal", "blue"]  # xen ke theo template hien tai (DANH SACH TAI GAME=teal, TOOL=blue)
ROW_CLASSES = ["c-blue", "c-red", "c-purple", "c-teal", "c-brown"]
ROW_ICONS = ["🎮", "🔫", "💕", "🥷", "⚔️", "🌪️", "🎯", "🕹️"]


def load_json(path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def site_name_spans(name):
    """Moi ky tu 1 mau, cycle qua .c1..c5 (dung lai CSS co san trong .banner .logo)."""
    parts = []
    i = 0
    for ch in name:
        if ch.strip() == "":
            parts.append(ch)
            continue
        cls = NAME_CLASSES[i % len(NAME_CLASSES)]
        parts.append('<span class="{}">{}</span>'.format(cls, html.escape(ch)))
        i += 1
    return "".join(parts)


def nav_row_links(categories, prefix=""):
    if not categories:
        return "    <!-- Chua co category nao -->"
    lines = []
    for cat in categories:
        href = "{}index.html#cat-{}".format(prefix, cat["slug"])
        lines.append('    <a href="{}">{}</a>'.format(href, html.escape(cat["name"])))
    return "\n".join(lines)


def banner_media_html(banner):
    url = (banner or {}).get("url") or ""
    kind = (banner or {}).get("type") or "image"
    if not url:
        return ""  # fallback: gradient placeholder co san trong CSS .wide-banner
    if kind == "video":
        return '    <video src="{}" autoplay muted loop playsinline></video>'.format(html.escape(url))
    return '    <img src="{}" alt="banner">'.format(html.escape(url))


def format_date(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return iso_str or ""


def download_href_and_attrs(post, depth_prefix):
    """Tra (href, extra_attrs) cho nut download, hoac (None, None) neu khong hop le."""
    dtype = post.get("download_type")
    if dtype == "link":
        url = post.get("download_url")
        if not url:
            return None, None
        return url, ' target="_blank" rel="noopener"'
    if dtype == "upload":
        f = post.get("download_file")
        if not f or not f.get("path"):
            return None, None
        if f.get("size", 0) > MAX_UPLOAD_BYTES:
            print("  [CANH BAO] '{}': file upload {} vuot 100MB, bo qua nut tai.".format(post["slug"], f.get("name")))
            return None, None
        return "{}{}".format(depth_prefix, f["path"]), ' download="{}"'.format(html.escape(f.get("name", "")))
    return None, None


def render(template_text, mapping):
    out = template_text
    for key, val in mapping.items():
        out = out.replace("{{" + key + "}}", val)
    return out


def build():
    site = load_json(DATA / "site.json", {})
    categories = load_json(DATA / "categories.json", [])
    posts_index = load_json(DATA / "posts.json", [])

    categories = sorted(categories, key=lambda c: c.get("order", 0))
    cat_by_id = {c["id"]: c for c in categories}

    posts_full = []
    for meta in posts_index:
        detail = load_json(DATA / "posts" / (meta["slug"] + ".json"))
        if detail is None:
            print("  [CANH BAO] Thieu file chi tiet cho bai '{}', bo qua.".format(meta["slug"]))
            continue
        posts_full.append(detail)

    build_index(site, categories, cat_by_id, posts_full)
    build_posts(site, categories, cat_by_id, posts_full)
    cleanup_removed_posts(posts_full)

    print("Build xong: {} category, {} bai viet.".format(len(categories), len(posts_full)))


def build_index(site, categories, cat_by_id, posts_full):
    template = (TEMPLATES / "index.html").read_text(encoding="utf-8")
    site_name = site.get("site_name", "WapVip.Pro")

    posts_by_cat = {}
    for p in posts_full:
        posts_by_cat.setdefault(p.get("category_id"), []).append(p)
    for lst in posts_by_cat.values():
        lst.sort(key=lambda p: p.get("created_at", ""), reverse=True)

    sections = []
    for idx, cat in enumerate(categories):
        hdr_cls = HDR_CLASSES[idx % len(HDR_CLASSES)]
        sections.append('  <div class="hdr {}" id="cat-{}">» {}</div>'.format(hdr_cls, cat["slug"], html.escape(cat["name"]).upper()))
        cat_posts = posts_by_cat.get(cat["id"], [])
        sections.append('  <div class="list">')
        if not cat_posts:
            sections.append('    <div class="row"><span class="ic">•</span><span>Chưa có bài viết nào</span></div>')
        else:
            for i, p in enumerate(cat_posts):
                row_cls = ROW_CLASSES[i % len(ROW_CLASSES)]
                icon = ROW_ICONS[i % len(ROW_ICONS)]
                href = "posts/{}/index.html".format(p["slug"])
                sections.append('    <div class="row"><span class="ic">{}</span><a href="{}" class="{}">{}</a></div>'.format(
                    icon, href, row_cls, html.escape(p["title"])))
        sections.append('  </div>')
        sections.append('')

    intro_paragraphs = "\n".join(
        "    <p>{}</p>".format(html.escape(p)) for p in site.get("intro_paragraphs", [])
    )

    mapping = {
        "PAGE_TITLE": html.escape(site_name + " - Tải Game Mobile Huyền Thoại, Tool Hack Miễn Phí"),
        "SITE_NAME_SPANS": site_name_spans(site_name),
        "INTRO_TITLE": html.escape(site.get("intro_title", "")),
        "INTRO_PARAGRAPHS": intro_paragraphs,
        "NAV_ROW_LINKS": nav_row_links(categories, prefix=""),
        "BANNER_MEDIA": banner_media_html(site.get("banner")),
        "BANNER_TEXT": html.escape((site.get("banner") or {}).get("text", "")),
        "CATEGORY_SECTIONS": "\n".join(sections),
        "FOOTER_TEXT": "{} © {}".format(html.escape(site_name), datetime.now().year),
    }
    out = render(template, mapping)
    (SITE_DIR / "index.html").write_text(out, encoding="utf-8")


def build_posts(site, categories, cat_by_id, posts_full):
    template = (TEMPLATES / "post.html").read_text(encoding="utf-8")
    site_name = site.get("site_name", "WapVip.Pro")
    depth_prefix = "../../"

    for post in posts_full:
        cat = cat_by_id.get(post.get("category_id"))
        cat_name = cat["name"] if cat else "Chưa Phân Loại"
        breadcrumb = (
            '<a href="../../index.html#cat-{}">{}</a>'.format(cat["slug"], html.escape(cat_name))
            if cat else html.escape(cat_name)
        )

        meta_parts = ['<span>{}</span>'.format(format_date(post.get("updated_at", "")))]
        meta_parts.append('<span class="tag">{}</span>'.format(html.escape(cat_name)))
        if post.get("game"):
            meta_parts.append('<span class="game">🎮 {}</span>'.format(html.escape(post["game"])))
        post_meta = " | ".join(meta_parts)

        href, attrs = download_href_and_attrs(post, depth_prefix)
        if href:
            download_button = '  <a class="dl-fab" href="{}"{}>⬇️ TẢI VỀ</a>'.format(html.escape(href), attrs)
        else:
            download_button = '  <!-- Chua co link/file tai, hoac file vuot 100MB -->'

        mapping = {
            "PAGE_TITLE": html.escape(post["title"] + " - " + site_name),
            "SITE_NAME_SPANS": site_name_spans(site_name),
            "NAV_ROW_LINKS": nav_row_links(categories, prefix=depth_prefix),
            "BREADCRUMB_CATEGORY": breadcrumb,
            "POST_TITLE": html.escape(post["title"]),
            "POST_META": post_meta,
            "DOWNLOAD_BUTTON": download_button,
            "CONTENT": post.get("content", ""),
            "FOOTER_TEXT": "{} © {}".format(html.escape(site_name), datetime.now().year),
        }
        out = render(template, mapping)

        out_dir = SITE_DIR / "posts" / post["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(out, encoding="utf-8")


def cleanup_removed_posts(posts_full):
    """Xoa thu muc html/posts/<slug> cua bai da bi xoa khoi data (khong con trong posts.json)."""
    posts_dir = SITE_DIR / "posts"
    if not posts_dir.exists():
        return
    valid_slugs = {p["slug"] for p in posts_full}
    for child in posts_dir.iterdir():
        if child.is_dir() and child.name not in valid_slugs:
            print("  Xoa bai cu khong con trong data: {}".format(child.name))
            for sub in sorted(child.rglob("*"), reverse=True):
                sub.unlink()
            child.rmdir()


if __name__ == "__main__":
    build()
