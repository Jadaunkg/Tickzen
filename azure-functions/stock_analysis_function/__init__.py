import azure.functions as func
import logging
import json
import os
from datetime import datetime, timezone
import redis
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

# Import your existing pipeline
import sys
sys.path.append('/home/site/wwwroot')
from automation_scripts.pipeline import run_pipeline

app = func.FunctionApp()

@app.function_name(name="stock_analysis")
@app.route(route="stock-analysis")
def stock_analysis_function(req: func.HttpRequest) -> func.HttpResponse:
    """Azure Function for stock analysis - replaces Celery task"""
    
    try:
        # Get request data
        req_body = req.get_json()
        ticker = req_body.get('ticker', '').strip().upper()
        user_uid = req_body.get('user_uid')
        room_id = req_body.get('room_id')
        
        if not ticker:
            return func.HttpResponse(
                json.dumps({"error": "Ticker symbol required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Initialize Redis connection
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            redis_client = redis.from_url(redis_url)
        else:
            # Fallback to Key Vault
            key_vault_url = os.getenv('AZURE_KEY_VAULT_URL')
            if key_vault_url:
                credential = DefaultAzureCredential()
                secret_client = SecretClient(vault_url=key_vault_url, credential=credential)
                redis_connection_string = secret_client.get_secret("redis-connection-string").value
                redis_client = redis.from_url(redis_connection_string)
            else:
                return func.HttpResponse(
                    json.dumps({"error": "Redis configuration not found"}),
                    status_code=500,
                    mimetype="application/json"
                )
        
        # Run stock analysis
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        app_root = "/home/site/wwwroot"
        
        logging.info(f"Starting stock analysis for {ticker}")
        
        # Run the pipeline (without socketio for Azure Functions)
        result = run_pipeline(ticker, timestamp, app_root)
        
        if result and len(result) >= 4:
            model_obj, forecast_obj, path_info, report_html = result[:4]
            
            # Store result in Redis for the web app to retrieve
            result_key = f"analysis_result:{ticker}:{timestamp}"
            result_data = {
                "ticker": ticker,
                "timestamp": timestamp,
                "path_info": path_info,
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
            
            redis_client.setex(result_key, 3600, json.dumps(result_data))  # 1 hour expiry
            
            # If room_id provided, store for WebSocket notification
            if room_id:
                notification_key = f"notification:{room_id}:{ticker}"
                notification_data = {
                    "type": "analysis_complete",
                    "ticker": ticker,
                    "timestamp": timestamp,
                    "status": "success"
                }
                redis_client.setex(notification_key, 300, json.dumps(notification_data))  # 5 min expiry
            
            return func.HttpResponse(
                json.dumps({
                    "status": "success",
                    "ticker": ticker,
                    "result_key": result_key,
                    "message": "Analysis completed successfully"
                }),
                status_code=200,
                mimetype="application/json"
            )
        else:
            return func.HttpResponse(
                json.dumps({
                    "status": "error",
                    "ticker": ticker,
                    "message": "Analysis failed - no data returned"
                }),
                status_code=500,
                mimetype="application/json"
            )
            
    except Exception as e:
        logging.error(f"Error in stock analysis function: {str(e)}")
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": f"Internal server error: {str(e)}"
            }),
            status_code=500,
            mimetype="application/json"
        ) 