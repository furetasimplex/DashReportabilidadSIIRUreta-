"""Read-only browser captures of the local Reclamo preview."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
phase = sys.argv[1]
out = HERE / phase
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe")
    page = browser.new_page(viewport={"width": 1366, "height": 768}, device_scale_factor=1)
    page.goto("http://127.0.0.1:8099/", wait_until="domcontentloaded", timeout=30000)
    page.locator("h1").first.wait_for(timeout=30000)
    page.wait_for_timeout(3500)
    for label, name in [("Resumen", "barra_y_validaciones"), ("Módulos", "modulos"), ("Ajustes y publicación", "publicacion")]:
        page.get_by_text(label, exact=True).first.click()
        page.wait_for_timeout(1500)
        page.screenshot(path=str(out / f"{name}_1366x768.png"), full_page=True)
        if label == "Módulos":
            page.get_by_text("Editar módulo", exact=True).first.click()
            page.wait_for_timeout(500)
            page.screenshot(path=str(out / "datos_base_1366x768.png"), full_page=True)
    browser.close()
