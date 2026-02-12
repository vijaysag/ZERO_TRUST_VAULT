# Blockchain Data Vault - Zero Trust Architecture

A secure data access system using blockchain technology with two-factor authentication.

## Quick Start

### Prerequisites
- Python 3.8+
- Ganache (for local blockchain)

### Setup

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Run Migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

3. **Create Admin User**
```bash
python manage.py createsuperuser
# Follow prompts and set role='admin' in Django admin or database
```

4. **Start Ganache**
- Open Ganache and start a workspace on `http://127.0.0.1:7545`

5. **Setup Email (SMTP)**
- Open the `.env` file in the project root.
- Enter your email address and an **App Password** (if using Gmail).
- The system will now send real OTPs to user emails!

6. **Deploy Smart Contract**
```bash
python blockchain/deploy_contract.py
```

6. **Run Server**
```bash
python manage.py runserver
```

7. **Access Application**
- Open browser: `http://localhost:8000`

## Features

### Admin
- Upload and manage data files
- View and process access requests
- Approve/reject with OTP verification
- View blockchain audit trail

### User
- Register with blockchain wallet
- Browse available data
- Request data access
- View data after admin approval + OTP
- All actions logged on blockchain

## Technology Stack
- **Backend**: Django, Python
- **Blockchain**: Ethereum, Solidity, Ganache, Web3.py
- **Frontend**: HTML, CSS, JavaScript
- **Security**: Two-Factor Authentication (OTP)

## Default Credentials
Create admin via `createsuperuser` command, then update role to 'admin' in database or Django admin panel.

## Notes
- OTPs are sent to console in development mode
- Check terminal for OTP codes during login/data access
- All blockchain transactions are logged with transaction hashes
