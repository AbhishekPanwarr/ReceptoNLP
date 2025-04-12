import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def generate_data(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get("https://www.linkedin.com/login")
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys("officialap1812@gmail.com")
        wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys("pratham1812")
        driver.find_element(By.XPATH, '//button[@type="submit"]').click()
        time.sleep(5)
        
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        time.sleep(3)
        
        # Scroll down to load all content
        for _ in range(5):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(1)
            
        print("Page title:", driver.title)
        print("Current URL:", driver.current_url)
        
        soup = BeautifulSoup(driver.page_source, "lxml")
        
        # Name
        name = ""
        name_tag = soup.find("h1")
        if name_tag:
            name = name_tag.get_text(strip=True)
            
        # Headline
        headline = ""
        headline_tag = soup.find("div", class_="text-body-medium")
        if headline_tag:
            headline = headline_tag.get_text(strip=True)
            
        # Location
        location = ""
        loc_tag = soup.find("span", class_="text-body-small")
        if loc_tag:
            location = loc_tag.get_text(strip=True)
            
        # Profile Image
        image_url = ""
        img_tag = soup.find("img", {"class": re.compile(r"profile-photo-edit__preview|pv-top-card-profile-picture__image")})
        if img_tag and img_tag.get("src"):
            image_url = img_tag["src"]
            
        # Cover Image
        cover_url = ""
        cover_div = soup.find("img", {"class": re.compile(r"cover-photo-image|profile-background-image")})
        if cover_div and cover_div.get("src"):
            cover_url = cover_div["src"]
        
        # About section
        about = ""
        # Try different possible selectors for the About section
        about_section = soup.find("section", {"id": re.compile(r"about-section|aboutSection")}) or \
                        soup.find("section", {"class": re.compile(r"about-section|summary")}) or \
                        soup.find("div", {"id": "about"}) or \
                        soup.find("div", {"class": "display-flex flex-column full-width"})
        
        if about_section:
            # Look for the paragraph in the about section
            about_text = about_section.find("div", {"class": re.compile(r"inline-show-more-text|pv-shared-text-with-see-more")})
            if about_text:
                about = about_text.get_text(strip=True)
        
        # If the above methods didn't work, try more generic approach
        if not about:
            # Try to find the About heading and then extract the text that follows
            about_headers = soup.find_all("h2")
            for header in about_headers:
                if "About" in header.get_text(strip=True):
                    # Get the parent section or div
                    parent = header.find_parent("section") or header.find_parent("div")
                    if parent:
                        # Find the text container in this section
                        text_div = parent.find("div", {"class": re.compile(r"inline-show-more-text|pv-shared-text-with-see-more")})
                        if text_div:
                            about = text_div.get_text(strip=True)
                            break
        
        return {
            "Name": name,
            "Headline": headline,
            "Location": location,
            "Profile_Image": image_url,
            "Cover_Image": cover_url,
            "About": about
        }
        
    except Exception as e:
        print("Error occurred:", e)
        return {}
        
    finally:
        driver.quit()



if __name__ == "__main__":
    profile_data = generate_data("https://www.linkedin.com/in/satyam-sharma-883b6a27b/")
    print(profile_data)
