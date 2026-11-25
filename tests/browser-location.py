"""Run against the disposable local QA API and Next dev server. No provider payments."""
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

WEB = "http://127.0.0.1:3262"
API = "http://127.0.0.1:5056/v1"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="chrome", args=["--enable-unsafe-swiftshader"])
    for width in (390, 1440):
        context = browser.new_context(viewport={"width":width,"height":900},
            geolocation={"latitude":5.556,"longitude":-0.182}, permissions=["geolocation"])
        request = context.request
        unique = uuid4().hex[:10]
        user = request.post(API+"/auth/register",data={"first_name":"Browser","last_name":"QA",
            "email":f"browser-{unique}@example.com","phone":"024"+str(int(unique,16))[-7:],"password":"LocalBrowserQA!123"})
        assert user.ok, (user.status, user.json().get("message"))
        session = user.json()
        page = context.new_page()
        page.set_default_timeout(60000)
        page.goto(WEB+"/bookings/new?service=Plumbing&run="+unique,wait_until="domcontentloaded",timeout=120000)
        page.evaluate("""([access,refresh])=>{localStorage.setItem('handework_access_token',access);
            localStorage.setItem('handework_refresh_token',refresh);localStorage.setItem('handework_last_active',String(Date.now()));}""",
            [session["access_token"],session["refresh_token"]])
        page.get_by_label("Job details").fill("Verify local booking location")
        page.get_by_role("button",name="Continue",exact=True).click()
        page.get_by_role("button",name="Use my location").click()
        expect(page.get_by_text("5.5560000,-0.1820000",exact=True)).to_be_visible()
        expect(page.locator("canvas.maplibregl-canvas")).to_be_visible()
        page.get_by_label("Job address",exact=False).first.fill("Osu QA location")
        page.get_by_label("Area",exact=True).fill("Osu")
        page.get_by_label("Date",exact=True).fill("2027-05-15")
        page.get_by_role("button",name="Continue",exact=True).click()
        page.get_by_label("Phone for job updates").fill("0244000001")
        page.locator('input[type=checkbox]').last.check()
        with page.expect_response(lambda r:r.request.method=="POST" and r.url.endswith("/v1/bookings")) as response:
            page.get_by_role("button",name="Confirm request").click()
        assert response.value.status==201, response.value.status
        data=response.value.json()
        details=request.get(API+"/bookings/"+data["id"],headers={"Authorization":"Bearer "+session["access_token"]})
        assert details.ok and details.json()["booking"]["reference"]==data["reference"]
        assert page.url.endswith("/bookings/"+data["id"])
        print(f"PASS {width}px GPS, MapLibre canvas, booking submission and persisted record",flush=True)
        context.close()
    browser.close()
