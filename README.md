# 🛡️ Zero Trust Architecture Based Secure Data Access System

A comprehensive secure data management platform built on Zero Trust principles, featuring Multi-Factor Authentication (TOTP), Role-Based Access Control, and Immutable Blockchain Auditing.

## 🚀 Key Features
*   **Zero Trust Identity**: Mandatory Authenticator App MFA (TOTP) for all users.
*   **Blockchain Auditing**: All data access requests and admin approvals are recorded on a private Ethereum ledger (Ganache).
*   **Role-Based Access**: Specialized modules for Admins (Upload/Modify/Approve) and Users (Browse/Request).
*   **Secure Document Vault**: Centralized repository for sensitive assets with strictly controlled access.
*   **MetaMask Integration**: Secure blockchain identity registration through browser wallet integration.

---

## 🛠️ Setup Instructions

Follow these steps to set up the environment, blockchain, and the Django application.

### 1. Prerequisites
Ensure the following are installed on your system:
*   **Python 3.9 - 3.13**
*   **Node.js & NPM** (needed for Ganache)
*   **Git**
*   **MetaMask Extension** (in Chrome, Edge, or Brave browser)

### 2. Project Initialisation
Open a terminal (PowerShell or Bash) and run:

```bash
# Clone the repository
git clone https://github.com/vijaysag/ZERO_TRUST_VAULT.git
cd ZERO_TRUST_VAULT

# Create a Virtual Environment
# (If 'python' fails on Windows, use 'py')
py -m venv venv

# Activate Virtual Environment
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt
```

### 3. Blockchain Setup (Ganache)
The vault requires a private Ethereum blockchain to be active.

1.  **Install Ganache CLI**:
    ```bash
    npm install -g ganache
    ```
2.  **Start the Blockchain**:
    Open a **separate** terminal and run:
    ```bash
    ganache --port 7545 --networkId 5777
    ```
    *Keep this terminal window open while using the application.*

### 4. Configuration (.env)
Create a file named `.env` in the root folder of the project and paste the following:

```env
DEBUG=True
SECRET_KEY=any-random-long-string
BLOCKCHAIN_PROVIDER=http://127.0.0.1:7545
CONTRACT_ADDRESS=
CONTRACT_ABI_PATH=contracts/DataAccessControl.json
```

### 5. Database & Smart Contract Deployment
In your main terminal (with the virtual environment active):

```bash
# Run Django Migrations
python manage.py makemigrations
python manage.py migrate

# Deploy the Audit Smart Contract
python deploy_contract.py
```
*The deployment script will automatically update your `.env` with the new `CONTRACT_ADDRESS`.*

### 6. Starting the Application
```bash
python manage.py runserver 9000
```
Visit the application at: **[http://localhost:9000](http://localhost:9000)**

---

## 🦊 Connecting MetaMask
To perform blockchain actions as a user:
1.  Open MetaMask and select **Add Network** -> **Add a network manually**.
2.  **RPC URL**: `http://127.0.0.1:7545`
3.  **Chain ID**: `1337` (or `5777`)
4.  **Currency**: ETH
5.  Import an account from your Ganache terminal using its **Private Key** to receive test ETH.

---

## 📂 Project Structure
*   `/core`: User models, Authentication logic, and TOTP services.
*   `/blockchain`: Ethereum/Web3 integration and deployment scripts.
*   `/data_management`: Admin repository tools (Upload/Modify).
*   `/access_control`: User request flow and Secure retrieval logic.
*   `/contracts`: Solidity smart contract for the audit ledger.
