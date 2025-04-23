import os
import re
import json
import uuid
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import pandas as pd
import logging
from openai import OpenAI
import requests

# Load environment variables and setup OpenAI
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# API Service URL
API_URL = 'http://localhost:5000'

# Configure Tesseract path (update this to your Tesseract installation path)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Setup Flask and logging
UPLOAD_FOLDER = 'uploads'
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'your-secret-key-here'  # Added for flash messages
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(
    filename='ats_logs.txt',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# ---------- OCR Function ----------
def extract_text_from_pdf(pdf_path):
    try:
        # Print Tesseract path for debugging
        print(f"Using Tesseract from: {pytesseract.pytesseract.tesseract_cmd}")
        images = convert_from_path(pdf_path, poppler_path=r"C:\poppler\Library\bin")
    except Exception as e:
        logging.error(f"❌ Failed to convert {pdf_path}: {e}")
        return None  # Will be skipped

    text = ""
    for i, img in enumerate(images):
        temp_img_path = f"{pdf_path}_{i}.png"
        img.save(temp_img_path, 'PNG')
        text += pytesseract.image_to_string(Image.open(temp_img_path)) + "\n"
        os.remove(temp_img_path)
    return text.strip()


# ---------- OpenAI Functions ----------
def extract_info_with_ai(text):
    prompt = (
        "Extract the following fields from the resume:\n"
        "Name:\nEmail:\nPhone:\nLinkedIn:\nGraduation Year:\n"
        "University:\nSkills:\n\nResume Text:\n" + text
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    reply = response.choices[0].message.content.strip()
    logging.info("📥 Prompt:\n" + prompt)
    logging.info("📤 GPT Reply:\n" + reply)
    return reply

def summarize_resume(text):
    prompt = "Summarize the following resume in 1-2 professional lines:\n\n" + text
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    reply = response.choices[0].message.content.strip()
    logging.info("📥 Prompt:\n" + prompt)
    logging.info("📤 GPT Reply:\n" + reply)
    return reply

# ---------- Routes ----------
@app.route('/', methods=['GET', 'POST'])
def index():
    extracted_info = []
    summaries = []
    raw_texts = []

    if request.method == 'POST':
        files = request.files.getlist('pdf_files')
        action = request.form.get('action')
        logging.info(f"User action: {action}")

        for file in files:
            filename = secure_filename(str(uuid.uuid4()) + "_" + file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            text = extract_text_from_pdf(filepath)
            if not text:
                continue  # Skip this file if OCR failed


            if action == 'read':
                raw_texts.append(text)

            elif action == 'extract':
                info = extract_info_with_ai(text)
                extracted_info.append(info)

            elif action == 'summarize':
                summary = summarize_resume(text)
                summaries.append(summary)

        num_files = max(len(extracted_info), len(summaries), 1)

        df = pd.DataFrame({
            'Name': [extract_field('Name', i) if i else '' for i in (extracted_info + [{}] * (num_files - len(extracted_info)))],
            'Email': [extract_field('Email', i) if i else '' for i in (extracted_info + [{}] * (num_files - len(extracted_info)))],
            'Phone': [extract_field('Phone', i) if i else '' for i in (extracted_info + [{}] * (num_files - len(extracted_info)))],
            'LinkedIn': [extract_field('LinkedIn', i) if i else '' for i in (extracted_info + [{}] * (num_files - len(extracted_info)))],
            'Graduation Year': [extract_field('Graduation Year', i) if i else '' for i in (extracted_info + [{}] * (num_files - len(extracted_info)))],
            'University': [extract_field('University', i) if i else '' for i in (extracted_info + [{}] * (num_files - len(extracted_info)))],
            'Skills': [extract_field('Skills', i) if i else '' for i in (extracted_info + [{}] * (num_files - len(extracted_info)))],
            'Summary': summaries + [''] * (num_files - len(summaries))
        })

        master_path = os.path.join(app.config['UPLOAD_FOLDER'], 'master_dataset.csv')

        # If the file exists, append without writing header
        if os.path.exists(master_path):
            df.to_csv(master_path, mode='a', index=False, header=False)
        else:
            df.to_csv(master_path, index=False)


        df.to_excel("Parsed_CVs.xlsx", index=False)

        return render_template(
            'index.html',
            extracted_info=extracted_info,
            summaries=summaries,
            raw_texts=raw_texts
        )

    return render_template('index.html')

@app.route('/download')
def download_file():
    return send_file("Parsed_CVs.xlsx", as_attachment=True)

@app.route('/search')
def search():
    keywords = request.args.get('keywords', '')
    department = request.args.get('department', '')
    job_title = request.args.get('job_title', '')

    # Get departments and job titles for filters
    departments_response = requests.get(f'{API_URL}/api/departments')
    job_titles_response = requests.get(f'{API_URL}/api/job-titles')
    
    departments = departments_response.json() if departments_response.ok else []
    job_titles = job_titles_response.json() if job_titles_response.ok else []

    # Build search URL with parameters
    search_params = {}
    if keywords:
        search_params['keywords'] = keywords
    if department:
        search_params['department'] = department
    if job_title:
        search_params['job_title'] = job_title

    # Make API request
    response = requests.get(f'{API_URL}/api/search', params=search_params)
    
    if response.ok:
        results = response.json()
        return render_template('search.html', 
                             results=results.get('results', []),
                             count=results.get('count', 0),
                             keywords=keywords,
                             department=department,
                             job_title=job_title,
                             departments=departments,
                             job_titles=job_titles)
    else:
        flash('Error searching CVs: ' + response.json().get('error', 'Unknown error'))
        return render_template('search.html', 
                             results=[],
                             count=0,
                             keywords=keywords,
                             department=department,
                             job_title=job_title,
                             departments=departments,
                             job_titles=job_titles)

@app.route('/cv/<int:cv_id>')
def view_cv(cv_id):
    # Get CV details from API
    response = requests.get(f'{API_URL}/api/cv/details/{cv_id}')
    
    if response.ok:
        cv_data = response.json()
        return render_template('view_cv.html', cv=cv_data)
    else:
        flash('Error retrieving CV details: ' + response.json().get('error', 'Unknown error'))
        return redirect(url_for('search'))

@app.route('/cv/file/<path:filename>')
def get_cv_file(filename):
    response = requests.get(f'{API_URL}/api/cv/{filename}', stream=True)
    
    if response.ok:
        return send_file(
            response.raw,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    else:
        flash('Error downloading CV file: ' + response.json().get('error', 'Unknown error'))
        return redirect(url_for('search'))

# ---------- Field Extraction Helper ----------
def extract_field(field, text):
    try:
        match = re.search(rf"{field}:\s*(.*)", text, re.IGNORECASE)
        return match.group(1).strip() if match else "N/A"
    except:
        return "N/A"

# ---------- Run Server ----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5055, debug=True)
