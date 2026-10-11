"""Capture local Reclamo preview screenshots at two desktop widths."""
from __future__ import annotations
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
phase = sys.argv[1] if len(sys.argv) == 2 else "before"
destination = HERE / phase
destination.mkdir(exist_ok=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe")
    for width, height in ((1366, 768), (1920, 1080), (390, 844)) if phase == "after" else ((1366, 768), (1920, 1080)):
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        page.goto("http://127.0.0.1:8099/", wait_until="domcontentloaded", timeout=30000)
        page.locator("h1").first.wait_for(timeout=30000)
        page.wait_for_timeout(8000)
        tabs = ("Resumen", "Reclamo diario", "Módulos", "Ajustes y publicación") if phase == "after" else (None,)
        for tab in tabs:
            if tab:
                page.get_by_text(tab, exact=True).first.click()
                page.wait_for_timeout(500)
            suffix = tab.lower().replace(" ", "_").replace("ó", "o").replace("ú", "u") if tab else "reclamo"
            path = destination / f"{suffix}_{width}x{height}.png"
            page.screenshot(path=str(path), full_page=True)
            print(path)
            if tab == "Módulos" and width != 390:
                page.get_by_text("Editar módulo", exact=True).first.click()
                page.wait_for_timeout(700)
                editor_path = destination / f"editor_{width}x{height}.png"
                page.screenshot(path=str(editor_path), full_page=True)
                print(editor_path)
        page.close()
    browser.close()
