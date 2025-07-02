import os
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import google.generativeai as genai
import pandas as pd
import time

st.set_page_config(page_title="AI-Powered Web Test Case Generator", layout="wide")

# Load external CSS
with open("assets/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Load layout template
with open("templates/layout.html") as f:
    st.markdown(f.read(), unsafe_allow_html=True)

# Gemini setup
api_key = os.getenv("GEMINI_API_KEY") or "AIzaSyDPGld8GvI8u4MirtorC6_T71K65DD5JYE"
genai.configure(api_key=api_key)
model = genai.GenerativeModel("models/gemini-2.5-pro")

def start_browser():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Enable headless if you want it invisible
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def generate_ai_test_case(element_summary):
    prompt = (
            f"Below is a description of web page elements:\n{element_summary}\n\n"
            " Generate very detailed functional and negative test cases, covering:\n"
            "- Field validation (e.g., required fields, format, length, value ranges)\n"
            "- UI behavior (e.g., button enable/disable, error messages, focus behavior)\n"
            "- Security scenarios (e.g., SQL injection, XSS, invalid characters)\n"
            "- Edge cases (e.g., empty inputs, very long inputs, special characters)\n"
            "- Navigation or link behavior (where applicable)\n"
            " Provide test cases as a **numbered list** with clear and precise steps."
        )
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating test cases: {e}"


def extract_elements_and_generate_tests(url):
    driver = start_browser()
    try:
        driver.get(url)
    except Exception as e:
        driver.quit()
        return [{"Element": "Error", "Test Cases": f"Could not load URL: {e}"}]

    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    summary = "Page element summary:\n"

    # Forms and inputs
    for form in soup.find_all('form'):
        form_id = form.get('id', 'N/A')
        form_class = ' '.join(form.get('class', []))
        summary += f"- Form ID: {form_id}, Classes: {form_class}\n"
        for inp in form.find_all('input'):
            summary += f"  - Input: type={inp.get('type', 'text')}, name={inp.get('name')}, id={inp.get('id')}, placeholder={inp.get('placeholder')}\n"

    # Buttons
    for button in soup.find_all('button'):
        summary += f"- Button: text='{button.text.strip()}', id={button.get('id')}, classes={button.get('class')}\n"

    # Links
    for link in soup.find_all('a'):
        summary += f"- Link: text='{link.text.strip()}', href='{link.get('href')}', id={link.get('id')}, classes={link.get('class')}\n"

    # Images
    for img in soup.find_all('img'):
        summary += f"- Image: src='{img.get('src')}', alt='{img.get('alt')}', id={img.get('id')}, classes={img.get('class')}\n"

    # Headings
    for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        summary += f"- Heading {h.name}: text='{h.text.strip()}'\n"

    # Labels
    for lbl in soup.find_all('label'):
        summary += f"- Label: text='{lbl.text.strip()}', for='{lbl.get('for')}'\n"

    # Dropdowns
    for sel in soup.find_all('select'):
        summary += f"- Dropdown: name='{sel.get('name')}', id='{sel.get('id')}'\n"
        for opt in sel.find_all('option'):
            summary += f"  - Option: value='{opt.get('value')}', text='{opt.text.strip()}'\n"

    # Checkboxes / radios
    for inp in soup.find_all('input'):
        if inp.get('type') in ['checkbox', 'radio']:
            summary += f"- {inp.get('type').capitalize()}: name='{inp.get('name')}', id='{inp.get('id')}', value='{inp.get('value')}'\n"

    driver.quit()

    if not summary.strip():
        summary = "No significant elements found."

    ai_result = generate_ai_test_case(summary)
    return [{"Element": "Page Summary", "Test Cases": ai_result}]

# Main UI
col1, col2 = st.columns([4, 1])
url = col1.text_input(" Enter URL (include http/https):", placeholder="https://example.com")
generate = col2.button("Generate Test Cases")

if generate:
    if url.startswith("http://") or url.startswith("https://"):
        with st.spinner("Scraping and generating..."):
            results = extract_elements_and_generate_tests(url)
            df = pd.DataFrame(results)
            st.success("Test cases generated!")
            for _, row in df.iterrows():
                with st.expander(f"{row['Element']}"):
                    st.markdown('<div class="result-box">', unsafe_allow_html=True)
                    st.code(row['Test Cases'])
                    st.markdown('</div>', unsafe_allow_html=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Test Cases (CSV)", csv, "test_cases.csv", "text/csv")
    else:
        st.error("❗ Please enter a valid URL starting with http:// or https://")
