"""Capture the read-only Cuadratura graph hover in local preview."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

phase = sys.argv[1]
out = Path(__file__).resolve().parent / phase
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe")
    page = browser.new_page(viewport={"width": 1366, "height": 768}, device_scale_factor=1)
    page.goto("http://127.0.0.1:8099/", wait_until="domcontentloaded", timeout=30000)
    page.get_by_text("Módulos", exact=True).first.click()
    page.locator("#g-cuadratura .barlayer .point:visible").first.wait_for(timeout=30000)
    for pad, label in (("1", "oxidos"), ("2", "sulfuros")):
        if pad == "2":
            page.locator("#cuadratura-pad-tabs").get_by_text("PAD 2 — Sulfuros", exact=True).click()
            page.locator("#g-cuadratura .barlayer .point:visible").first.wait_for(timeout=30000)
        point = page.locator("#g-cuadratura .barlayer .point:visible").nth(4)
        point.scroll_into_view_if_needed()
        box = point.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.wait_for_timeout(700)
        image = out / f"hover_{label}_1366x768.png"
        page.screenshot(path=str(image))
        print(label, "points", page.locator("#g-cuadratura .barlayer .point:visible").count(), "hover", page.locator(".hoverlayer").text_content(), image)
    browser.close()
