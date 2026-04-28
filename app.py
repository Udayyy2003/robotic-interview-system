import os
import json
import smtplib
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
from docx import Document
import fitz  # PyMuPDF for PDF parsing

UPLOAD_FOLDER = 'resumes'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

app = Flask(__name__)
app.secret_key = 'secret-key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

HR_EMAIL = 'udayp1298@gmail.com'
SENDER_EMAIL = 'rushityadav06@gmail.com'
EMAIL_PASSWORD = 'aelm gfiq vtjz ozfr'  # Replace with env variable in production


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_requirements():
    with open('requirements.json', 'r') as f:
        return json.load(f)


def save_requirements(data):
    with open('requirements.json', 'w') as f:
        json.dump(data, f, indent=4)


def extract_text_from_pdf(file_path):
    text = ""
    doc = fitz.open(file_path)
    for page in doc:
        text += page.get_text()
    return text


def extract_text_from_docx(file_path):
    text = ""
    doc = Document(file_path)
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text


def extract_resume_text(file_path):
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    return ""


def match_requirements(text, requirements):
    matched = True
    missing = []

    lower_text = text.lower()

    for field, keywords in requirements.items():
        found = False
        for keyword in keywords:
            if keyword.lower() in lower_text:
                found = True
                break
        if not found:
            matched = False
            missing.append((field, keywords))

    return matched, missing


def send_email_with_attachment(file_path, subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = HR_EMAIL
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    # Attach file
    with open(file_path, 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
        msg.attach(part)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)
    except smtplib.SMTPException as e:
        print(f"Failed to send email: {e}")


@app.route('/')
def index():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        flash("No file part")
        return render_template('upload.html')

    resume_file = request.files['resume']
    if resume_file.filename == '':
        flash("No selected file")
        return render_template('upload.html')

    filename = secure_filename(resume_file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    resume_file.save(file_path)

    resume_text = extract_resume_text(file_path)
    requirements = load_requirements()

    matched, missing = match_requirements(resume_text, requirements)

    if matched:
        send_email_with_attachment(file_path, 'Resume Matches Requirements', 'The resume matches all job requirements.')
        flash("✅ Resume matched all requirements and was sent to HR.")
    else:
        flash("❌ Resume did not meet all requirements. No email sent.")
        print("Missing fields:", [key for key, _ in missing])

    return render_template('upload.html')


# @app.route('/requirements', methods=['GET', 'POST'])
@app.route('/requirements', methods=['GET', 'POST'])
def requirements():
    if request.method == 'POST':
        form_data = {}
        for key in request.form:
            form_data[key] = [v.strip() for v in request.form.get(key, '').split(',') if v.strip()]
        save_requirements(form_data)
        flash("✅ Requirements updated successfully.")
        return redirect(url_for('requirements'))

    current_requirements = load_requirements()
    return render_template('requirements.html', data=current_requirements)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
