# User Data Dashboard

A web application to filter and extract user data from RevenueCat and OneSignal.

## Setup

### Backend
bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py


### Frontend
bash
cd frontend
npm install
npm start


## Data Files

Place your data files in the `backend/data` directory:
- `revenuecat.json`: RevenueCat user data
- `onesignal.json`: OneSignal user data

## Environment Variables

Frontend environment variables are stored in `.env.development` for development.
EOF
