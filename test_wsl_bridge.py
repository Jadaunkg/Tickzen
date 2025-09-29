#!/usr/bin/env python3
"""
Test script for WSL Prophet Bridge
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_wsl_bridge():
    """Test the WSL Prophet Bridge"""
    try:
        print("Testing WSL Prophet Bridge...")

        # Import the bridge
        from Models.wsl_prophet_bridge import create_wsl_prophet_bridge
        print("✅ WSL Prophet Bridge imported successfully")

        # Try to create bridge (this will check WSL availability)
        bridge = create_wsl_prophet_bridge()
        print("✅ WSL Prophet Bridge created successfully")

        # Test with simple data
        import pandas as pd
        import numpy as np

        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        values = 100 + np.sin(np.arange(100) * 2 * np.pi / 30) * 10 + np.random.normal(0, 2, 100)

        df = pd.DataFrame({
            'ds': dates,
            'y': values
        })

        print("🔄 Testing Prophet model training via WSL...")
        forecast_df, model_info = bridge.fit_predict(df, forecast_periods=30)
        print("✅ Prophet model trained successfully via WSL!")
        print(f"   - Forecast shape: {forecast_df.shape}")
        print(f"   - Sample prediction: {forecast_df['yhat'].iloc[-1]:.2f}")

        return True

    except Exception as e:
        print(f"❌ WSL Prophet Bridge test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_wsl_bridge()
    sys.exit(0 if success else 1)