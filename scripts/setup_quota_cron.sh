#!/bin/bash
#
# Quota Reset Cron Job Setup for Production
# This script sets up a monthly cron job to automatically reset user quotas
#
# Usage: 
#   chmod +x setup_quota_cron.sh
#   sudo ./setup_quota_cron.sh
#

set -e

echo "=================================="
echo "Quota Reset Cron Job Setup"
echo "=================================="
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_PATH="/usr/bin/python3"  # Adjust if needed
RESET_SCRIPT="$PROJECT_ROOT/scripts/reset_monthly_quotas.py"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/quota_reset.log"

# Create logs directory if it doesn't exist
if [ ! -d "$LOG_DIR" ]; then
    echo "Creating logs directory: $LOG_DIR"
    mkdir -p "$LOG_DIR"
fi

# Check if reset script exists
if [ ! -f "$RESET_SCRIPT" ]; then
    echo "ERROR: Reset script not found at $RESET_SCRIPT"
    exit 1
fi

echo "Configuration:"
echo "  Project Root: $PROJECT_ROOT"
echo "  Python Path: $PYTHON_PATH"
echo "  Reset Script: $RESET_SCRIPT"
echo "  Log File: $LOG_FILE"
echo ""

# Create cron job entry
CRON_ENTRY="1 0 1 * * cd $PROJECT_ROOT && $PYTHON_PATH $RESET_SCRIPT >> $LOG_FILE 2>&1"

echo "Cron job entry:"
echo "  $CRON_ENTRY"
echo ""

# Check if cron job already exists
EXISTING_CRON=$(crontab -l 2>/dev/null | grep -F "$RESET_SCRIPT" || true)

if [ -n "$EXISTING_CRON" ]; then
    echo "WARNING: A cron job for quota reset already exists:"
    echo "  $EXISTING_CRON"
    echo ""
    read -p "Do you want to replace it? (y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. No changes made."
        exit 0
    fi
    
    # Remove existing cron job
    crontab -l 2>/dev/null | grep -v -F "$RESET_SCRIPT" | crontab -
    echo "Existing cron job removed."
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo ""
echo "✅ Cron job successfully created!"
echo ""
echo "The quota reset will run:"
echo "  - Every month on the 1st"
echo "  - At 12:01 AM (00:01)"
echo "  - Logs will be written to: $LOG_FILE"
echo ""
echo "To verify, run: crontab -l"
echo "To remove, run: crontab -e (and delete the line)"
echo ""
echo "Manual test command:"
echo "  cd $PROJECT_ROOT && $PYTHON_PATH $RESET_SCRIPT"
echo ""
