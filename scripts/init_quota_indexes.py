"""
Initialize Firestore Indexes for Quota System

This script deploys the Firestore indexes defined in firestore.indexes.json
"""

import os
import sys
import subprocess
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def deploy_firestore_indexes():
    """Deploy Firestore indexes using Firebase CLI"""
    try:
        # Get project root directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        # Check if firestore.indexes.json exists
        indexes_file = os.path.join(project_root, 'firestore.indexes.json')
        if not os.path.exists(indexes_file):
            logger.error(f"firestore.indexes.json not found at {indexes_file}")
            return False
        
        logger.info(f"Found firestore.indexes.json at {indexes_file}")
        
        # Deploy indexes
        logger.info("Deploying Firestore indexes...")
        result = subprocess.run(
            ['firebase', 'deploy', '--only', 'firestore:indexes'],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Firestore indexes deployed successfully!")
            logger.info(result.stdout)
            return True
        else:
            logger.error("❌ Failed to deploy Firestore indexes")
            logger.error(result.stderr)
            return False
            
    except FileNotFoundError:
        logger.error("Firebase CLI not found. Please install it: npm install -g firebase-tools")
        return False
    except Exception as e:
        logger.error(f"Error deploying indexes: {e}")
        return False


def deploy_firestore_rules():
    """Deploy Firestore security rules"""
    try:
        # Get project root directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        # Check if firestore.rules exists
        rules_file = os.path.join(project_root, 'firestore.rules')
        if not os.path.exists(rules_file):
            logger.error(f"firestore.rules not found at {rules_file}")
            return False
        
        logger.info(f"Found firestore.rules at {rules_file}")
        
        # Deploy rules
        logger.info("Deploying Firestore security rules...")
        result = subprocess.run(
            ['firebase', 'deploy', '--only', 'firestore:rules'],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Firestore rules deployed successfully!")
            logger.info(result.stdout)
            return True
        else:
            logger.error("❌ Failed to deploy Firestore rules")
            logger.error(result.stderr)
            return False
            
    except Exception as e:
        logger.error(f"Error deploying rules: {e}")
        return False


def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("Firestore Quota System Initialization")
    logger.info("=" * 60)
    
    # Deploy indexes
    logger.info("\n[Step 1/2] Deploying Firestore Indexes...")
    if deploy_firestore_indexes():
        logger.info("✅ Indexes deployed")
    else:
        logger.warning("⚠️  Index deployment failed (you may need to deploy manually)")
    
    # Deploy rules
    logger.info("\n[Step 2/2] Deploying Firestore Security Rules...")
    if deploy_firestore_rules():
        logger.info("✅ Rules deployed")
    else:
        logger.warning("⚠️  Rules deployment failed (you may need to deploy manually)")
    
    logger.info("\n" + "=" * 60)
    logger.info("Initialization complete!")
    logger.info("=" * 60)
    logger.info("\nNext steps:")
    logger.info("1. Run 'python scripts/migrate_user_quotas.py' to initialize quotas for existing users")
    logger.info("2. Integrate quota checks into your application routes")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
