from web3 import Web3
from django.conf import settings
import json
import os
from pathlib import Path


class BlockchainService:
    """Service to interact with Ethereum blockchain via Web3"""
    
    def __init__(self):
        self.w3 = None
        self.contract = None
        self.contract_address = None
        self.admin_account = None
        self.connect()
    
    def connect(self):
        """Connect to Ganache blockchain"""
        try:
            self.w3 = Web3(Web3.HTTPProvider(settings.BLOCKCHAIN_PROVIDER))
            
            if not self.w3.is_connected():
                print("Warning: Unable to connect to blockchain")
                return False
            
            print(f"Connected to blockchain: {settings.BLOCKCHAIN_PROVIDER}")
            
            # Get available accounts
            accounts = self.w3.eth.accounts
            if accounts:
                self.admin_account = accounts[0]
                print(f"Admin account: {self.admin_account}")
            
            # Load contract if deployed
            self.load_contract()
            
            return True
        except Exception as e:
            print(f"Blockchain connection error: {str(e)}")
            return False
    
    def load_contract(self):
        """Load deployed contract"""
        try:
            # Check if contract address is configured
            if not settings.CONTRACT_ADDRESS:
                print("Contract not yet deployed")
                return False
            
            # Load ABI
            abi_path = settings.CONTRACT_ABI_PATH
            if not os.path.exists(abi_path):
                print(f"ABI file not found: {abi_path}")
                return False
            
            with open(abi_path, 'r') as f:
                contract_abi = json.load(f)
            
            self.contract_address = settings.CONTRACT_ADDRESS
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.contract_address),
                abi=contract_abi
            )
            
            print(f"Contract loaded at: {self.contract_address}")
            return True
        except Exception as e:
            print(f"Error loading contract: {str(e)}")
            return False
    
    def deploy_contract(self, compiled_contract):
        """Deploy the smart contract to blockchain"""
        try:
            if not self.w3 or not self.w3.is_connected():
                raise Exception("Not connected to blockchain")
            
            # Get contract interface
            contract_interface = compiled_contract['contracts']['DataAccessControl.sol']['DataAccessControl']
            abi = contract_interface['abi']
            bytecode = contract_interface['evm']['bytecode']['object']
            
            # Create contract instance
            Contract = self.w3.eth.contract(abi=abi, bytecode=bytecode)
            
            # Deploy contract
            tx_hash = Contract.constructor().transact({
                'from': self.admin_account,
                'gas': 3000000
            })
            
            # Wait for transaction receipt
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            self.contract_address = tx_receipt.contractAddress
            self.contract = self.w3.eth.contract(
                address=self.contract_address,
                abi=abi
            )
            
            # Save ABI to file
            abi_path = settings.CONTRACT_ABI_PATH
            os.makedirs(os.path.dirname(abi_path), exist_ok=True)
            with open(abi_path, 'w') as f:
                json.dump(abi, f, indent=2)
            
            print(f"Contract deployed at: {self.contract_address}")
            print(f"Transaction hash: {tx_hash.hex()}")
            
            return {
                'address': self.contract_address,
                'tx_hash': tx_hash.hex(),
                'abi': abi
            }
        except Exception as e:
            print(f"Error deploying contract: {str(e)}")
            raise
    
    def create_access_request(self, user_address, username, data_id, data_name):
        """Create an access request on blockchain"""
        try:
            if not self.contract:
                print("Contract not loaded")
                return None
            
            tx_hash = self.contract.functions.createAccessRequest(
                Web3.to_checksum_address(user_address),
                username,
                data_id,
                data_name
            ).transact({'from': self.admin_account, 'gas': 200000})
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'tx_hash': tx_hash.hex(),
                'block_number': receipt['blockNumber'],
                'status': receipt['status']
            }
        except Exception as e:
            print(f"Error creating access request: {str(e)}")
            return None
    
    def process_access_request(self, request_id, approved):
        """Process (approve/reject) an access request on blockchain"""
        try:
            if not self.contract:
                print("Contract not loaded")
                return None
            
            tx_hash = self.contract.functions.processAccessRequest(
                request_id,
                approved
            ).transact({'from': self.admin_account, 'gas': 200000})
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'tx_hash': tx_hash.hex(),
                'block_number': receipt['blockNumber'],
                'status': receipt['status']
            }
        except Exception as e:
            print(f"Error processing access request: {str(e)}")
            return None
    
    def record_data_upload(self, data_id, data_name, uploaded_by, ipfs_hash=''):
        """Record data upload on blockchain"""
        try:
            if not self.contract:
                print("Contract not loaded")
                return None
            
            tx_hash = self.contract.functions.recordDataUpload(
                data_id,
                data_name,
                Web3.to_checksum_address(uploaded_by),
                ipfs_hash
            ).transact({'from': self.admin_account, 'gas': 200000})
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'tx_hash': tx_hash.hex(),
                'block_number': receipt['blockNumber'],
                'status': receipt['status']
            }
        except Exception as e:
            print(f"Error recording data upload: {str(e)}")
            return None
    
    def log_data_access(self, user_address, username, data_id, action='view'):
        """Log data access on blockchain"""
        try:
            if not self.contract:
                print("Contract not loaded")
                return None
            
            tx_hash = self.contract.functions.logDataAccess(
                Web3.to_checksum_address(user_address),
                username,
                data_id,
                action
            ).transact({'from': self.admin_account, 'gas': 200000})
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                'tx_hash': tx_hash.hex(),
                'block_number': receipt['blockNumber'],
                'status': receipt['status']
            }
        except Exception as e:
            print(f"Error logging data access: {str(e)}")
            return None
    
    def get_pending_requests_count(self):
        """Get count of pending requests from blockchain"""
        try:
            if not self.contract:
                return 0
            
            count = self.contract.functions.getPendingRequestsCount().call()
            return count
        except Exception as e:
            print(f"Error getting pending requests count: {str(e)}")
            return 0
    
    def get_request_details(self, request_id):
        """Get request details from blockchain"""
        try:
            if not self.contract:
                return None
            
            details = self.contract.functions.getRequestDetails(request_id).call()
            
            return {
                'user_address': details[0],
                'username': details[1],
                'data_id': details[2],
                'data_name': details[3],
                'timestamp': details[4],
                'approved': details[5],
                'processed': details[6]
            }
        except Exception as e:
            print(f"Error getting request details: {str(e)}")
            return None
    
    def assign_wallet_address(self, user_index):
        """Assign a wallet address to a user"""
        try:
            accounts = self.w3.eth.accounts
            if user_index < len(accounts):
                return accounts[user_index]
            return None
        except Exception as e:
            print(f"Error assigning wallet address: {str(e)}")
            return None


# Singleton instance
blockchain_service = BlockchainService()
