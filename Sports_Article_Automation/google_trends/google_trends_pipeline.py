"""
Google Trends Automation Pipeline
Integrates Google Trends collection with the automation system
Runs on schedule or via API trigger
"""

import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class GoogleTrendsAutomationPipeline:
    """Pipeline for automating Google Trends data collection and management"""

    def __init__(self, project_root: Optional[str] = None):
        """Initialize the automation pipeline"""
        if project_root is None:
            project_root = Path(__file__).resolve().parent

        self.project_root = Path(project_root)
        self.trends_db_path = self.project_root / "google_trends_database.json"
        self.log_file = self.project_root.parent / "logs" / "trends_automation.log"

        # Ensure logs directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def run_full_collection(self) -> Dict:
        """
        Run complete Google Trends collection pipeline
        Collects all categories and regions, updates database
        """
        logger.info("=" * 80)
        logger.info("🌍 GOOGLE TRENDS AUTOMATION PIPELINE STARTED")
        logger.info("=" * 80)
        logger.info(f"Start Time: {datetime.utcnow().isoformat()}")

        results = {
            'success': False,
            'timestamp': datetime.utcnow().isoformat(),
            'stage_results': {},
            'total_new_trends': 0,
            'total_errors': 0,
            'errors': []
        }

        try:
            # Import here to avoid circular imports
            from Sports_Article_Automation.google_trends.google_trends_collector import GoogleTrendsCollector

            # Stage 1: Initialize collector
            logger.info("\n📊 Stage 1: Initializing Google Trends Collector...")
            try:
                collector = GoogleTrendsCollector(database_path=str(self.trends_db_path))
                results['stage_results']['initialization'] = 'success'
                logger.info("✅ Collector initialized successfully")
            except Exception as e:
                error_msg = f"Failed to initialize collector: {str(e)}"
                logger.error(f"❌ {error_msg}")
                results['stage_results']['initialization'] = 'failed'
                results['errors'].append(error_msg)
                results['total_errors'] += 1
                raise

            # Stage 2: Run collection pipeline
            logger.info("\n🔄 Stage 2: Running Collection Pipeline...")
            try:
                pipeline_results = collector.run_collection_pipeline()
                
                results['stage_results']['collection'] = 'success'
                results['total_new_trends'] = pipeline_results.get('total_new_trends', 0)
                
                logger.info(f"✅ Collection completed")
                logger.info(f"   - New Trends: {pipeline_results.get('total_new_trends', 0)}")
                logger.info(f"   - Total in DB: {pipeline_results.get('total_trends_collected', 0)}")
                logger.info(f"   - Categories: {', '.join(pipeline_results.get('categories_collected', []))}")
                
                if pipeline_results.get('errors'):
                    results['total_errors'] += len(pipeline_results['errors'])
                    results['errors'].extend(pipeline_results['errors'])
                    logger.warning(f"⚠️  Collection had {len(pipeline_results['errors'])} errors")
                    
            except Exception as e:
                error_msg = f"Collection pipeline failed: {str(e)}"
                logger.error(f"❌ {error_msg}")
                results['stage_results']['collection'] = 'failed'
                results['errors'].append(error_msg)
                results['total_errors'] += 1
                raise

            # Stage 3: Data cleanup (remove old trends)
            logger.info("\n🧹 Stage 3: Cleaning Old Data...")
            try:
                removed = collector.clear_old_trends(days=30)
                results['stage_results']['cleanup'] = 'success'
                logger.info(f"✅ Cleaned {removed} old trends")
            except Exception as e:
                logger.warning(f"⚠️  Cleanup failed (non-critical): {str(e)}")
                results['stage_results']['cleanup'] = 'warning'

            # Final status
            results['success'] = True if results['total_errors'] == 0 else False
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {str(e)}")
            results['success'] = False
            results['errors'].append(f"Pipeline execution failed: {str(e)}")

        # Log summary
        logger.info("\n" + "=" * 80)
        logger.info("📈 GOOGLE TRENDS AUTOMATION PIPELINE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Status: {'✅ SUCCESS' if results['success'] else '❌ FAILED'}")
        logger.info(f"New Trends: {results['total_new_trends']}")
        logger.info(f"Errors: {results['total_errors']}")
        logger.info(f"Timestamp: {results['timestamp']}")
        
        if results['errors']:
            logger.info("\nErrors encountered:")
            for error in results['errors']:
                logger.error(f"  - {error}")

        logger.info("=" * 80)

        return results

    def schedule_daily_collection(self, hour: int = 9, minute: int = 0) -> Dict:
        """
        Schedule daily Google Trends collection
        
        Args:
            hour: Hour to run collection (0-23, UTC)
            minute: Minute to run collection (0-59)
            
        Returns:
            Scheduling configuration
        """
        logger.info(f"Scheduling daily Google Trends collection at {hour:02d}:{minute:02d} UTC")

        schedule_config = {
            'enabled': True,
            'frequency': 'daily',
            'time': f'{hour:02d}:{minute:02d}',
            'timezone': 'UTC',
            'created_at': datetime.utcnow().isoformat(),
            'next_run': self._calculate_next_run(hour, minute)
        }

        logger.info(f"✅ Schedule configured: {schedule_config}")
        return schedule_config

    def _calculate_next_run(self, hour: int, minute: int) -> str:
        """Calculate next scheduled run time"""
        now = datetime.utcnow()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if next_run <= now:
            next_run += timedelta(days=1)

        return next_run.isoformat()

    def get_automation_status(self) -> Dict:
        """Get current automation status"""
        try:
            from Sports_Article_Automation.google_trends.google_trends_collector import GoogleTrendsCollector
            
            collector = GoogleTrendsCollector(database_path=str(self.trends_db_path))
            
            return {
                'status': 'active',
                'trends_in_database': len(collector.trends_data),
                'last_collection': collector.last_collection_time,
                'total_collections': collector.collection_count,
                'database_path': str(self.trends_db_path),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting automation status: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def export_trends_report(self, output_format: str = 'json') -> Dict:
        """
        Export trends data as report
        
        Args:
            output_format: 'json', 'csv', or 'html'
            
        Returns:
            Export result with file path
        """
        try:
            from Sports_Article_Automation.google_trends.google_trends_collector import GoogleTrendsCollector
            
            collector = GoogleTrendsCollector(database_path=str(self.trends_db_path))
            
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            if output_format == 'json':
                output_file = self.project_root / "generated_data" / f"trends_report_{timestamp}.json"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                report_data = {
                    'export_timestamp': datetime.utcnow().isoformat(),
                    'total_trends': len(collector.trends_data),
                    'trends': collector.trends_data,
                    'by_category': self._group_by_category(collector.trends_data),
                    'by_region': self._group_by_region(collector.trends_data)
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ Report exported to {output_file}")
                return {
                    'success': True,
                    'format': output_format,
                    'file_path': str(output_file),
                    'total_trends': len(collector.trends_data)
                }
            else:
                return {
                    'success': False,
                    'error': f'Unsupported format: {output_format}'
                }
                
        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _group_by_category(self, trends: list) -> Dict:
        """Group trends by category"""
        grouped = {}
        for trend in trends:
            category = trend.get('category', 'unknown')
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(trend)
        return {k: len(v) for k, v in grouped.items()}

    def _group_by_region(self, trends: list) -> Dict:
        """Group trends by region"""
        grouped = {}
        for trend in trends:
            region = trend.get('region', 'unknown')
            if region not in grouped:
                grouped[region] = []
            grouped[region].append(trend)
        return {k: len(v) for k, v in grouped.items()}


# Standalone execution
if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    # Configure logging
    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'trends_automation.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Run pipeline
    pipeline = GoogleTrendsAutomationPipeline(project_root)
    results = pipeline.run_full_collection()
    
    # Exit with appropriate code
    sys.exit(0 if results['success'] else 1)
