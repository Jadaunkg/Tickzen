Stock Report Automation Portal
🚀 Introduction
The Stock Report Automation Portal is a web application that automates the process of generating and publishing stock analysis reports. It lets you manage multiple websites, configure report options, and automatically post detailed stock content to WordPress blogs.

The system collects data such as stock prices, macroeconomic indicators, and company fundamentals. It then performs technical and fundamental analysis, builds forecasts using Facebook Prophet, and compiles this information into professional reports.

The portal uses Firebase for user accounts and profile management, and integrates with WordPress via the REST API.

Purpose: Make it easier and faster to create high-quality, data-driven financial articles for multiple websites.

✨ Key Features
Secure Login System
Login with email/password or Google — powered by Firebase Authentication.

Profile Dashboard
Each user has a profile area to view and manage account details and website configurations.

Site Profiles (WordPress Integration)

Add/edit site profiles for WordPress blogs.

Enter author credentials, site URL, category IDs, report sections, and publishing settings.

Store all data safely in Firestore.

Automation Runner

Run automation for selected site profiles.

Upload ticker lists via Excel or enter them manually.

Generate a set number of reports per site.

View status and progress.

Stock Report Generator

Collects stock data and economic indicators.

Performs both technical and fundamental analysis.

Uses Facebook Prophet to generate forecasts.

Composes the final HTML report with multiple sections like:

Company Overview

Valuation

Financial Health

Technical Charts

Forecasts

FAQs and Disclaimers

WordPress Auto-Publishing

Uses API to publish reports directly.

Handles scheduling and limits.

Supports multiple authors.

📁 Project Structure
bash
Copy
Edit
current automation tool/
├── main_portal_app.py           # Main Flask app
├── auto_publisher.py            # Handles WordPress publishing
├── data_collection.py           # Stock price and macro data
├── technical_analysis.py        # RSI, MACD, Bollinger Bands, etc.
├── fundamental_analysis.py      # Company profiles, financial ratios
├── prophet_model.py             # Forecasting using Facebook Prophet
├── firebase_admin_setup.py      # Firebase backend connection
├── static/                      # CSS + JavaScript
│   ├── css/style.css
│   └── js/
│       ├── main.js              # JS for automation & forms
│       └── firebase-init.js     # Firebase client-side auth
├── templates/                   # HTML pages
│   ├── homepage.html
│   ├── login.html
│   ├── register.html
│   ├── manage_profiles.html
│   └── run_automation_page.html
├── config/
│   └── firebase-service-account-key.json  # 🔒 DO NOT commit this
├── .env                         # Environment variables
├── requirements.txt             # Dependencies
└── README.md
⚙️ Setup Instructions
✅ Requirements
Python 3.8 or higher

Firebase project with:

Authentication (Email/Password, Google Sign-In)

Firestore database

WordPress site with Application Passwords enabled

🔧 Installation Steps
Clone the Project

bash
Copy
Edit
git clone <your-repo-url>
cd <project-folder>
Set Up Virtual Environment

bash
Copy
Edit
python -m venv venv
venv\Scripts\activate  # On Windows
# or
source venv/bin/activate  # On macOS/Linux
Install Python Dependencies

bash
Copy
Edit
pip install -r requirements.txt
Set Up Firebase

Place your firebase-service-account-key.json file in config/

Never commit this file to GitHub (add it to .gitignore)

In your .env:

ini
Copy
Edit
FLASK_SECRET_KEY=your_secret_here
GOOGLE_APPLICATION_CREDENTIALS=./config/firebase-service-account-key.json
Update Frontend Firebase Config
In static/js/firebase-init.js, add your actual Firebase config:

js
Copy
Edit
const firebaseConfig = {
  apiKey: "...",
  authDomain: "...",
  projectId: "...",
  ...
};
Run the App

bash
Copy
Edit
python main_portal_app.py
Visit http://localhost:5000 to use the portal.

🧪 How to Use the Portal
Login/Register
Use email or Google to log in.

Manage Site Profiles
Add your WordPress blogs, author info, and reporting preferences.

Run Automation
Choose profiles, upload tickers or enter them manually, and click to start. The backend will fetch data, build reports, and publish them.

🛠️ Technologies Used
Stack	Tools
Backend	Python, Flask
Frontend	HTML, CSS, JavaScript
Auth	Firebase Authentication
Database	Firebase Firestore
Modeling	Facebook Prophet, Pandas, NumPy
APIs	yfinance, FRED (macro data)
Publishing	WordPress REST API (auto_publisher.py)

🔒 Security Best Practices
Never share .env or Firebase key files publicly.

Use strong secrets and rotate them periodically.

Sanitize all user input before processing.

Use HTTPS in production and set proper CORS rules.

Monitor dependencies for security issues.

🚧 Possible Improvements
Better frontend status reporting during automation.

Graphs and visualizations of stock trends in dashboard.

Secure author credentials storage (e.g., vault service).

Add email notifications for report publishing.

Role-based access control (admin/editor).

Test suite and CI/CD integration.

📌 Final Note
This project is actively evolving and designed for internal or private use. If you plan to open-source it, be sure to remove any sensitive information and write a proper contribution guide.