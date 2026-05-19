import os
import re
import time
import traceback
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

LOGIN_URL = "https://ers.tup.edu.ph/aims/students/"
SCHED_URL = "https://ers.tup.edu.ph/aims/students/schedule.php?mainID=105&menuDesc=Schedule"

DAY_MAP = {
    "M":   "Monday",
    "T":   "Tuesday",
    "W":   "Wednesday",
    "TH":  "Thursday",
    "F":   "Friday",
    "S":   "Saturday",
    "SUN": "Sunday",
}

def parse_schedule(schedule_str):
    clean = schedule_str.split(" - ")[-1].strip()
    match = re.match(r"(\w+)\s+([\d:APM]+-[\d:APM]+)\s*(.*)", clean)
    if match:
        day_code = match.group(1).strip()
        return {
            "day":  DAY_MAP.get(day_code, day_code),
            "time": match.group(2).strip(),
            "room": match.group(3).strip() or "TBA"
        }
    return {"day": "N/A", "time": "N/A", "room": "TBA"}

def format_units(lec, lab):
    parts = []
    if lec != "0":
        parts.append(f"Lec: {lec}")
    if lab != "0":
        parts.append(f"Lab: {lab}")
    return ", ".join(parts)

def get_chrome_driver():
    options = Options()
    # Run invisibly so users do not see a browser window while fetching.
    options.add_argument("--headless=new")
    options.add_argument("--disable-extensions")
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--window-size=1920,1080")
    
    # Block images to save massive amounts of RAM and load faster
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    # Check if running in Docker (Render deployment)
    if os.environ.get("RUNNING_IN_DOCKER"):
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
        return webdriver.Chrome(service=service, options=options)
    else:
        # Local execution (Desktop app testing)
        return webdriver.Chrome(options=options)

def scrape_schedule(student_id: str, password: str, birthdate: str):
    driver = None
    try:
        driver = get_chrome_driver()
        wait = WebDriverWait(driver, 25) # Increased wait time for slower portal loads
        
        # ── LOGIN ─────────────────────────────────────
        driver.get(LOGIN_URL)
        wait.until(EC.presence_of_element_located((By.NAME, "username")))

        driver.find_element(By.NAME, "username").send_keys(student_id)
        driver.find_element(By.NAME, "password").send_keys(password)

        # Bypass the readonly datepicker
        driver.execute_script("""
            var field = document.getElementsByName('bdate')[0];
            field.removeAttribute('readonly');
            field.value = arguments[0];
            field.dispatchEvent(new Event('input',  { bubbles: true }));
            field.dispatchEvent(new Event('change', { bubbles: true }));
            field.dispatchEvent(new Event('blur',   { bubbles: true }));
            if (typeof jQuery !== 'undefined') {
                jQuery(field).val(arguments[0]).trigger('change').trigger('blur');
            }
        """, birthdate)

        time.sleep(1)

        btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        driver.execute_script("arguments[0].click()", btn)

        wait.until(EC.url_changes(LOGIN_URL))

        # Check if login failed (still on the login page)
        if "students/" == driver.current_url.split("aims/")[-1]:
            return {"success": False, "error": "Invalid credentials or portal timeout."}

        # ── SCRAPE SCHEDULE ───────────────────────────
        driver.get(SCHED_URL)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "dbtable")))

        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table", class_="dbtable")
        rows = table.find_all("tr", bgcolor="white")

        schedule = []
        for row in rows:
            cols = row.find_all("td")
            if cols:
                parsed = parse_schedule(cols[7].text.strip())
                schedule.append({
                    "no":          cols[0].text.strip(),
                    "code":        cols[1].text.strip(),
                    "description": cols[2].text.strip(),
                    "lec":         cols[3].text.strip(),
                    "lab":         cols[4].text.strip(),
                    "units":       cols[5].text.strip(),
                    "faculty":     cols[6].text.strip(),
                    "day":         parsed["day"],
                    "time":        parsed["time"],
                    "room":        parsed["room"],
                })

        return {"success": True, "schedule": schedule}

    except Exception as e:
        # Capture the exact error and line number for debugging
        error_log = traceback.format_exc()
        error_name = type(e).__name__
        print(f"SCRAPER EXCEPTION:\n{error_log}")
        return {"success": False, "error": f"[{error_name}] {str(e)}"}

    finally:
        if driver:
            driver.quit()
