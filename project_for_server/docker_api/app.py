"""
Мини-сервис превью Яндекс-видео
POST /preview  {"items": ["id", "https://..."]}
→ {"<canonical-url>": "<base64-jpeg-or-null>", ...}
"""

import asyncio
import base64
import io
import re
import ssl
from typing import Dict, List, Optional
import certifi
import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image
from playwright.async_api import async_playwright, Browser


WIDTH             = 640       # итоговая ширина превью
TIMEOUT           = 10        # сек; html/картинка/страница
NET_CONCURRENCY   = 20        # параллельные HTTP-запросы
PAGE_CONCURRENCY  = 4         # одновременных вкладок Chrome
PLAYER_PREFIX     = "https://runtime.video.cloud.yandex.net/player/video/"



class Items(BaseModel):    # ---------- Pydantic -----------------
    items: List[str]


_RE_POSTER_JSON = re.compile(r'"poster"\s*:\s*"([^"]+)"')


async def fetch_html(cli: httpx.AsyncClient, url: str) -> Optional[str]:
    try:
        r = await cli.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        return r.text
    except Exception:
        return None


def extract_poster(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", property="og:image")
    if meta and meta.get("content"):
        return meta["content"]

    div = soup.find("div", class_="vjs-poster")
    if div and (sty := div.get("style")):
        m = re.search(r'url\("?([^")]+)"?', sty)
        if m:
            return m.group(1)
    m = _RE_POSTER_JSON.search(html)
    return m.group(1) if m else None


async def download(cli: httpx.AsyncClient, url: str) -> Optional[bytes]:
    try:
        r = await cli.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def to_jpeg(raw: bytes, width: int = WIDTH) -> bytes:
    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", img.size, "white")
        bg.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
        img = bg
    else:
        img = img.convert("RGB")
    if img.width > width:
        h = int(img.height * width / img.width)
        img = img.resize((width, h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


async def grab_with_browser(browser: Browser, url: str) -> Optional[bytes]:
    ctx = await browser.new_context(ignore_https_errors=True,
                                    viewport={"width": 1280, "height": 720})
    page = await ctx.new_page()
    full = url + ("&" if "?" in url else "?") + "autoplay=1"
    try:
        await page.goto(full, timeout=TIMEOUT*1000)
        await page.wait_for_selector("video", timeout=TIMEOUT*1000)
    except Exception:
        await ctx.close()
        return None

    poster = await page.eval_on_selector("video", "v=>v?.poster") or ""
    if poster:
        try:
            await page.goto(poster, timeout=TIMEOUT*1000)
            png = await page.screenshot(type="png", full_page=True)
            await ctx.close()
            return png
        except Exception:
            pass

    try:
        b64 = await page.evaluate(
            """v=>{const c=document.createElement('canvas');
                   c.width=v.videoWidth||v.clientWidth;
                   c.height=v.videoHeight||v.clientHeight;
                   const ctx=c.getContext('2d');
                   try{ctx.drawImage(v,0,0,c.width,c.height);
                       return c.toDataURL('image/png').split(',')[1];}
                   catch(e){return null;}}""",
            await page.query_selector("video"))
        if b64:
            await ctx.close()
            return base64.b64decode(b64)
    except Exception:
        pass

    try:
        png = await page.screenshot(type="png")
        await ctx.close()
        return png
    except Exception:
        await ctx.close()
        return None


# ---------- генерация превью -----------
async def generate(urls: List[str]) -> Dict[str, Optional[bytes]]:
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    limits = httpx.Limits(max_connections=NET_CONCURRENCY)

    async with httpx.AsyncClient(verify=ssl_ctx, limits=limits) as cli, \
               async_playwright() as pw:

        browser = await pw.chromium.launch(
            channel="chrome", headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--ignore-certificate-errors",
                  "--autoplay-policy=no-user-gesture-required"])

        sem = asyncio.Semaphore(PAGE_CONCURRENCY)
        res: Dict[str, Optional[bytes]] = {}

        async def handle(u: str):
            html = await fetch_html(cli, u)
            poster = extract_poster(html) if html else None
            if poster:
                img = await download(cli, poster)
                if img:
                    res[u] = img
                    return
            async with sem:
                png = await grab_with_browser(browser, u)
            res[u] = png

        await asyncio.gather(*(handle(u) for u in urls))
        await browser.close()
        return res


# ---------- FastAPI --------------------
app = FastAPI(title="Yandex-video preview")


@app.post("/preview")
async def preview(data: Items):
    if not data.items:
        raise HTTPException(400, "items list is empty")

    urls = [
        x if x.startswith("http") else f"{PLAYER_PREFIX}{x}"
        for x in data.items
    ]

    raw = await generate(urls)
    return {
        url: (base64.b64encode(to_jpeg(img)).decode() if img else None)
        for url, img in raw.items()
    }
