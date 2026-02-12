"""
Reddit API Credentials Verification Script
TickZen v2.3 - Phase 3, Day 3

Purpose: Verify Reddit API credentials are configured correctly before running real data tests

Usage:
    python testing/verify_reddit_credentials.py

Expected Output:
    ✅ All checks pass → Ready for Day 3 testing
    ❌ Any check fails → Follow troubleshooting steps

Date: February 9, 2026
"""

import os
import sys

def verify_credentials():
    """Verify Reddit API credentials and dependencies"""
    
    print("\n" + "="*70)
    print(" "*15 + "REDDIT API CREDENTIALS VERIFICATION")
    print("="*70 + "\n")
    
    all_checks_passed = True
    
    # Check 1: Environment Variables
    print("📋 Checking Environment Variables...")
    
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    user_agent = os.getenv('REDDIT_USER_AGENT')
    
    if client_id:
        if client_id in ['your_client_id_here', '', 'None']:
            print("   ❌ REDDIT_CLIENT_ID is placeholder value")
            print("      Set to your actual Reddit app client ID")
            all_checks_passed = False
        else:
            print(f"   ✅ REDDIT_CLIENT_ID: {client_id[:8]}... (redacted)")
    else:
        print("   ❌ REDDIT_CLIENT_ID not set")
        print("      See PHASE_3_DAY_3_SETUP.md for setup instructions")
        all_checks_passed = False
    
    if client_secret:
        if client_secret in ['your_client_secret_here', '', 'None']:
            print("   ❌ REDDIT_CLIENT_SECRET is placeholder value")
            print("      Set to your actual Reddit app client secret")
            all_checks_passed = False
        else:
            print(f"   ✅ REDDIT_CLIENT_SECRET: {client_secret[:8]}... (redacted)")
    else:
        print("   ❌ REDDIT_CLIENT_SECRET not set")
        print("      See PHASE_3_DAY_3_SETUP.md for setup instructions")
        all_checks_passed = False
    
    if user_agent:
        if 'your_' in user_agent.lower() or user_agent == '':
            print("   ❌ REDDIT_USER_AGENT is placeholder value")
            print("      Format: 'TickZen/1.0 (by /u/your_reddit_username)'")
            all_checks_passed = False
        else:
            print(f"   ✅ REDDIT_USER_AGENT: {user_agent}")
    else:
        print("   ❌ REDDIT_USER_AGENT not set")
        print("      Format: 'TickZen/1.0 (by /u/your_reddit_username)'")
        all_checks_passed = False
    
    # Check 2: PRAW Library
    print("\n📦 Checking Dependencies...")
    
    try:
        import praw
        print(f"   ✅ PRAW Library Installed: {praw.__version__}")
    except ImportError:
        print("   ❌ PRAW not installed")
        print("      Install with: pip install praw==7.7.1")
        all_checks_passed = False
        return all_checks_passed
    
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        print(f"   ✅ VADER Sentiment Library Installed")
    except ImportError:
        print("   ❌ vaderSentiment not installed")
        print("      Install with: pip install vaderSentiment==3.3.2")
        all_checks_passed = False
        return all_checks_passed
    
    # Check 3: Reddit API Connection (if credentials set)
    if client_id and client_secret and user_agent:
        if client_id not in ['your_client_id_here', '', 'None']:
            print("\n🌐 Testing Reddit API Connection...")
            
            try:
                reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent
                )
                
                # Try to access a popular subreddit
                subreddit = reddit.subreddit('wallstreetbets')
                _ = subreddit.display_name  # Trigger API call
                
                print(f"   ✅ Successfully connected to Reddit API")
                print(f"   ✅ Can access r/{subreddit.display_name}")
                
            except Exception as e:
                print(f"   ❌ Failed to connect to Reddit API")
                print(f"      Error: {str(e)[:60]}...")
                print(f"\n      Troubleshooting:")
                print(f"      1. Verify Client ID and Secret are correct")
                print(f"      2. Check that app type is 'script' (not 'web app')")
                print(f"      3. Regenerate credentials at https://www.reddit.com/prefs/apps")
                all_checks_passed = False
    
    # Check 4: RedditSentimentAnalyzer Class
    print("\n🔧 Checking TickZen Components...")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from analysis_scripts.reddit_sentiment_analyzer import RedditSentimentAnalyzer
        print("   ✅ RedditSentimentAnalyzer class available")
    except ImportError as e:
        print(f"   ❌ Cannot import RedditSentimentAnalyzer")
        print(f"      Error: {str(e)}")
        print(f"      Verify file exists: analysis_scripts/reddit_sentiment_analyzer.py")
        all_checks_passed = False
    
    # Final Summary
    print("\n" + "="*70)
    if all_checks_passed:
        print(" "*20 + "🎉 ALL CHECKS PASSED! 🎉")
        print("="*70)
        print("\n✅ Reddit API credentials verified")
        print("✅ Dependencies installed")
        print("✅ API connection working")
        print("✅ TickZen components ready")
        print("\n📊 Ready to run Day 3 real data tests:")
        print("   cd tickzen2")
        print("   python -m pytest testing/test_reddit_real_data.py -v")
        print("\n" + "="*70 + "\n")
        return True
    else:
        print(" "*20 + "❌ SETUP INCOMPLETE")
        print("="*70)
        print("\n⚠️  Please fix the issues above before running Day 3 tests")
        print("\n📖 Setup Guide: PHASE_3_DAY_3_SETUP.md")
        print("📖 Full Guide: REDDIT_API_SETUP_GUIDE.md")
        print("\n" + "="*70 + "\n")
        return False


if __name__ == '__main__':
    success = verify_credentials()
    sys.exit(0 if success else 1)
