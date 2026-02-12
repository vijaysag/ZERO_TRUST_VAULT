"""
Script to compile and deploy the DataAccessControl smart contract to Ganache
"""
import json
import os
import sys
from pathlib import Path
from solcx import compile_source, install_solc, set_solc_version
from web3 import Web3

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blockchain_data_vault.settings')
import django
django.setup()

from django.conf import settings
from blockchain.services import blockchain_service


def compile_contract():
    """Compile the Solidity contract"""
    print("Installing Solidity compiler...")
    install_solc('0.8.0')
    set_solc_version('0.8.0')
    
    print("Reading contract source...")
    contract_path = project_root / 'contracts' / 'DataAccessControl.sol'
    
    with open(contract_path, 'r') as f:
        contract_source = f.read()
    
    print("Compiling contract...")
    compiled_sol = compile_source(
        contract_source,
        output_values=['abi', 'bin']
    )
    
    return compiled_sol


def deploy_contract():
    """Deploy the compiled contract to Ganache"""
    print("\n" + "="*60)
    print("BLOCKCHAIN DATA VAULT - Smart Contract Deployment")
    print("="*60 + "\n")
    
    # Check blockchain connection
    if not blockchain_service.w3 or not blockchain_service.w3.is_connected():
        print("❌ Error: Not connected to blockchain")
        print(f"   Make sure Ganache is running on {settings.BLOCKCHAIN_PROVIDER}")
        return False
    
    print(f"✓ Connected to blockchain: {settings.BLOCKCHAIN_PROVIDER}")
    print(f"✓ Admin account: {blockchain_service.admin_account}")
    
    # Compile contract
    try:
        compiled_contract = compile_contract()
        print("✓ Contract compiled successfully")
    except Exception as e:
        print(f"❌ Error compiling contract: {str(e)}")
        return False
    
    # Deploy contract
    try:
        print("\nDeploying contract...")
        deployment_result = blockchain_service.deploy_contract(compiled_contract)
        
        print("\n" + "="*60)
        print("✓ CONTRACT DEPLOYED SUCCESSFULLY!")
        print("="*60)
        print(f"\nContract Address: {deployment_result['address']}")
        print(f"Transaction Hash: {deployment_result['tx_hash']}")
        print(f"ABI saved to: {settings.CONTRACT_ABI_PATH}")
        
        # Update settings file with contract address
        settings_path = project_root / 'blockchain_data_vault' / 'settings.py'
        with open(settings_path, 'r') as f:
            settings_content = f.read()
        
        # Replace CONTRACT_ADDRESS = None with actual address
        updated_content = settings_content.replace(
            "CONTRACT_ADDRESS = None",
            f"CONTRACT_ADDRESS = '{deployment_result['address']}'"
        )
        
        with open(settings_path, 'w') as f:
            f.write(updated_content)
        
        print(f"\n✓ Settings updated with contract address")
        print("\n" + "="*60)
        print("DEPLOYMENT COMPLETE!")
        print("="*60 + "\n")
        
        return True
    except Exception as e:
        print(f"\n❌ Error deploying contract: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = deploy_contract()
    sys.exit(0 if success else 1)
