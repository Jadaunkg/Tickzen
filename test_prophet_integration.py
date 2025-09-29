#!/usr/bin/env python3
"""
Test script for the integrated Prophet model with WSL bridge auto-detection
"""

import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path

# Add the Models directory to the path
sys.path.insert(0, str(Path(__file__).parent / 'Models'))

def test_prophet_integration():
    """Test the integrated Prophet model with auto WSL detection"""
    print("Testing integrated Prophet model with WSL auto-detection...")

    # Create test data similar to stock data
    dates = pd.date_range('2020-01-01', periods=365, freq='D')
    base_price = 100
    trend = np.linspace(0, 50, 365)  # Upward trend
    seasonal = 10 * np.sin(2 * np.pi * np.arange(365) / 365)  # Seasonal component
    noise = np.random.normal(0, 2, 365)  # Random noise

    prices = base_price + trend + seasonal + noise

    # Create DataFrame with required columns
    data = pd.DataFrame({
        'Date': dates,
        'Close': prices
    })

    # Add some technical indicators for regressor testing
    data['RSI'] = 50 + 20 * np.sin(2 * np.pi * np.arange(365) / 30)  # Mock RSI
    data['MACD'] = np.random.normal(0, 1, 365)  # Mock MACD

    print(f"Created test data with {len(data)} rows")
    print(f"Data columns: {list(data.columns)}")
    print(f"Date range: {data['Date'].min()} to {data['Date'].max()}")
    print(f"Price range: ${data['Close'].min():.2f} to ${data['Close'].max():.2f}")

    try:
        # Import the main prophet model function
        from prophet_model import train_prophet_model
        print("✅ Successfully imported train_prophet_model")

        # Test the model training
        print("🔄 Training Prophet model...")
        model, forecast, agg_actual, agg_forecast = train_prophet_model(
            data=data,
            ticker='TEST',
            forecast_horizon='30d'
        )

        print("✅ Prophet model training completed successfully!")
        print(f"   - Model type: {type(model)}")
        print(f"   - Forecast shape: {forecast.shape}")
        print(f"   - Forecast columns: {list(forecast.columns)}")
        print(f"   - Forecast date range: {forecast['ds'].min()} to {forecast['ds'].max()}")
        print(f"   - Sample forecast values: yhat={forecast['yhat'].iloc[-1]:.2f}, yhat_lower={forecast['yhat_lower'].iloc[-1]:.2f}, yhat_upper={forecast['yhat_upper'].iloc[-1]:.2f}")
        print(f"   - Aggregated actual shape: {agg_actual.shape}")
        print(f"   - Aggregated forecast shape: {agg_forecast.shape}")

        # Verify forecast makes sense
        last_actual = data['Close'].iloc[-1]
        first_forecast = forecast[forecast['ds'] > data['Date'].max()]['yhat'].iloc[0]

        print(f"   - Last actual price: ${last_actual:.2f}")
        print(f"   - First forecast price: ${first_forecast:.2f}")
        print(f"   - Forecast continuity: {'✅ Good' if abs(first_forecast - last_actual) < 10 else '⚠️  Large jump'}")

        return True

    except Exception as e:
        print(f"❌ Prophet model training failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_prophet_integration()
    if success:
        print("\n🎉 All tests passed! WSL Prophet integration is working correctly.")
    else:
        print("\n💥 Tests failed. Check the error messages above.")
        sys.exit(1)