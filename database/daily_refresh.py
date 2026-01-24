#!/usr/bin/env python3
"""
Daily Refresh Script
====================

Run this script daily at a fixed time (e.g., 6 PM) to refresh stock data.
Syncs all stocks due for update and generates report.

Schedule with:
  Cron (Linux/Mac): 0 22 * * * /path/to/daily_refresh.py
  Windows Task Scheduler: C:\\python.exe C:\\path\\daily_refresh.py
  APScheduler: See end of file for integration
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.sync_manager import StockDataSyncManager, SyncType
from database.stock_registry import StockRegistry

# Configure logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"daily_refresh_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class DailyRefreshManager:
    """Manages daily refresh operations"""
    
    def __init__(self):
        """Initialize refresh manager"""
        self.sync_mgr = StockDataSyncManager()
        self.registry = StockRegistry()
        self.start_time = datetime.now()
    
    def run_refresh(self, max_stocks: Optional[int] = None, dry_run: bool = False) -> bool:
        """
        Run daily refresh for all due stocks.
        
        Args:
            max_stocks: Limit number of stocks (for testing)
            dry_run: Simulate without writing
            
        Returns:
            True if successful
        """
        
        logger.info("="*70)
        logger.info("DAILY REFRESH STARTED")
        logger.info("="*70)
        
        try:
            # Get stocks due for refresh
            due_stocks = self.registry.get_due_for_sync(hours=24)
            
            if not due_stocks:
                logger.info("No stocks due for refresh")
                return True
            
            if max_stocks:
                due_stocks = due_stocks[:max_stocks]
            
            symbols = [s["symbol"] for s in due_stocks]
            
            logger.info(f"Found {len(symbols)} stocks due for refresh")
            logger.info(f"Stocks: {', '.join(symbols[:10])}" + 
                       (" ..." if len(symbols) > 10 else ""))
            
            # Sync all due stocks
            logger.info("\nStarting sync...")
            results = self.sync_mgr.sync_multiple(
                symbols,
                sync_type=SyncType.DAILY,
                dry_run=dry_run
            )
            
            # Print report
            self._print_report(results, dry_run)
            
            # Save report
            self._save_report(results)
            
            # Log summary
            successful = len([r for r in results if r.status == "success"])
            partial = len([r for r in results if r.status == "partial"])
            failed = len([r for r in results if r.status == "failed"])
            
            logger.info("="*70)
            logger.info("DAILY REFRESH COMPLETED")
            logger.info(f"Summary: {successful} success, {partial} partial, {failed} failed")
            logger.info(f"Duration: {self._get_duration()}")
            logger.info("="*70)
            
            # Return success if no failures
            return failed == 0
        
        except Exception as e:
            logger.error(f"Refresh failed: {e}", exc_info=True)
            return False
    
    def _print_report(self, results, dry_run: bool) -> None:
        """Print sync report"""
        
        print("\n" + "="*70)
        print("SYNC REPORT")
        print("="*70)
        
        if dry_run:
            print("DRY RUN - No data written")
            print()
        
        for result in results:
            status_symbol = {
                "success": "✓",
                "partial": "⚠",
                "failed": "✗"
            }.get(result.status, "?")
            
            print(f"{status_symbol} {result.stock_symbol:10} | "
                  f"Records: {result.total_records_processed:7,} | "
                  f"Quality: {result.data_quality_score:.2f} | "
                  f"Status: {result.status}")
            
            if result.error_message:
                print(f"    Error: {result.error_message}")
        
        print("="*70)
        
        # Summary statistics
        report = self.sync_mgr.get_sync_report()
        print(f"\nStatistics:")
        print(f"  Total Syncs: {report['total_syncs']}")
        print(f"  Success: {report['successful']}")
        print(f"  Partial: {report['partial']}")
        print(f"  Failed: {report['failed']}")
        print(f"  Avg Quality: {report['avg_quality_score']:.2f}")
        print(f"  Total Records: {report['total_records_processed']:,}")
        print()
    
    def _save_report(self, results) -> None:
        """Save report to JSON file"""
        
        report_data = self.sync_mgr.get_sync_report()
        
        # Save to reports directory
        reports_dir = Path(__file__).parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / f"sync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            logger.info(f"Report saved: {report_file}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
    
    def _get_duration(self) -> str:
        """Get formatted duration"""
        duration = datetime.now() - self.start_time
        minutes = duration.total_seconds() / 60
        return f"{minutes:.1f} minutes"


def send_email_report(success: bool, refresh_mgr: DailyRefreshManager) -> None:
    """
    Send email report of sync results.
    
    Requires: pip install python-dotenv sendgrid
    """
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
    except ImportError:
        logger.warning("SendGrid not installed. Skipping email report.")
        return
    
    api_key = os.getenv("SENDGRID_API_KEY")
    to_email = os.getenv("SYNC_REPORT_EMAIL")
    
    if not api_key or not to_email:
        logger.warning("SendGrid email not configured")
        return
    
    # Build report
    report = refresh_mgr.sync_mgr.get_sync_report()
    
    subject = f"Tickzen Sync Report - {report['timestamp']}"
    status = "✓ SUCCESS" if success else "✗ FAILED"
    
    body = f"""
Tickzen Daily Refresh Report
{status}

Timestamp: {report['timestamp']}

Summary:
- Total Syncs: {report['total_syncs']}
- Successful: {report['successful']}
- Partial: {report['partial']}
- Failed: {report['failed']}
- Avg Quality: {report['avg_quality_score']:.2f}

For details, check: https://your-domain.com/admin/sync-logs
    """
    
    try:
        sg = SendGridAPIClient(api_key)
        mail = Mail(
            from_email="noreply@tickzen.com",
            to_emails=to_email,
            subject=subject,
            plain_text_content=body
        )
        
        response = sg.send(mail)
        logger.info(f"Email sent: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


def main():
    """Main entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Tickzen daily refresh script")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't write)")
    parser.add_argument("--max-stocks", type=int, help="Limit number of stocks")
    parser.add_argument("--email", action="store_true", help="Send email report")
    
    args = parser.parse_args()
    
    # Run refresh
    refresh_mgr = DailyRefreshManager()
    success = refresh_mgr.run_refresh(
        max_stocks=args.max_stocks,
        dry_run=args.dry_run
    )
    
    # Send email if requested
    if args.email:
        send_email_report(success, refresh_mgr)
    
    # Exit with appropriate code
    return 0 if success else 1


# ============================================================================
# APScheduler Integration
# ============================================================================

def setup_scheduler():
    """
    Set up APScheduler for automatic daily refresh.
    
    Usage:
        from daily_refresh import setup_scheduler
        scheduler = setup_scheduler()
        scheduler.start()
    """
    
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        return None
    
    scheduler = BackgroundScheduler()
    
    def scheduled_refresh():
        """Scheduled refresh job"""
        try:
            refresh_mgr = DailyRefreshManager()
            success = refresh_mgr.run_refresh()
            
            if success:
                logger.info("Scheduled refresh completed successfully")
            else:
                logger.error("Scheduled refresh had failures")
        
        except Exception as e:
            logger.error(f"Scheduled refresh failed: {e}", exc_info=True)
    
    # Schedule at 6 PM daily (18:00)
    scheduler.add_job(
        scheduled_refresh,
        'cron',
        hour=18,
        minute=0,
        id='daily_stock_refresh'
    )
    
    logger.info("Scheduler configured: Daily refresh at 18:00")
    
    return scheduler


# ============================================================================
# Flask Integration
# ============================================================================

def create_flask_route():
    """
    Create Flask route for manual refresh trigger.
    
    Usage:
        from flask import Flask
        from daily_refresh import create_flask_route
        
        app = Flask(__name__)
        app.add_url_rule("/admin/refresh", view_func=create_flask_route())
    """
    
    from flask import jsonify
    
    def refresh_route():
        """Handle manual refresh"""
        try:
            refresh_mgr = DailyRefreshManager()
            success = refresh_mgr.run_refresh()
            
            report = refresh_mgr.sync_mgr.get_sync_report()
            
            return jsonify({
                "success": success,
                "report": report
            })
        
        except Exception as e:
            logger.error(f"Manual refresh failed: {e}", exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500
    
    return refresh_route


if __name__ == "__main__":
    sys.exit(main())

# ============================================================================
# Cron Scheduling Examples
# ============================================================================
"""
Linux/Mac - Add to crontab (crontab -e):

# Daily refresh at 6 PM
0 18 * * * /usr/bin/python3 /path/to/daily_refresh.py >> /path/to/logs/cron.log 2>&1

# Daily refresh with email at 6:15 PM
15 18 * * * /usr/bin/python3 /path/to/daily_refresh.py --email >> /path/to/logs/cron.log 2>&1

# Daily dry run at 5 PM for testing
0 17 * * * /usr/bin/python3 /path/to/daily_refresh.py --dry-run
"""

# ============================================================================
# Windows Task Scheduler Examples
# ============================================================================
"""
Windows - Create via Command Prompt (as Administrator):

# Daily refresh at 6 PM
schtasks /create /tn TickzenDailySync /tr "C:\\python.exe C:\\path\\daily_refresh.py" /sc daily /st 18:00

# Daily refresh with email
schtasks /create /tn TickzenDailySyncWithEmail /tr "C:\\python.exe C:\\path\\daily_refresh.py --email" /sc daily /st 18:00

# Delete task
schtasks /delete /tn TickzenDailySync /f
"""

# ============================================================================
# Systemd Timer Examples (Linux)
# ============================================================================
"""
Create /etc/systemd/system/tickzen-sync.service:

[Unit]
Description=Tickzen Daily Stock Sync
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /path/to/daily_refresh.py
User=www-data
StandardOutput=journal
StandardError=journal

Create /etc/systemd/system/tickzen-sync.timer:

[Unit]
Description=Tickzen Daily Sync Timer
Requires=tickzen-sync.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 18:00:00
Persistent=true

[Install]
WantedBy=timers.target

Enable:
systemctl enable tickzen-sync.timer
systemctl start tickzen-sync.timer
"""
