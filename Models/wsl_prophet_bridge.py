#!/usr/bin/env python3
"""
WSL Prophet Bridge - Run Prophet models in Windows Subsystem for Linux

This module provides a seamless interface to run Facebook Prophet time series
forecasting in WSL, avoiding Windows compatibility issues with CmdStan.
"""

import os
import sys
import json
import subprocess
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple, Any
import platform

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WSLProphetBridge:
    """
    Bridge to run Prophet models in WSL environment
    """

    def __init__(self, wsl_distro: str = None):
        """
        Initialize WSL Prophet Bridge

        Args:
            wsl_distro: WSL distribution name (e.g., 'Ubuntu'). If None, uses default.
        """
        self.wsl_distro = wsl_distro
        self.python_executable = "python3"
        self.prophet_script_path = None

        # Check if running on Windows
        if platform.system() != 'Windows':
            raise RuntimeError("WSL Prophet Bridge is only supported on Windows")

        # Verify WSL is available
        self._check_wsl_availability()

        # Set up WSL environment
        self._setup_wsl_environment()

    def _check_wsl_availability(self) -> None:
        """Check if WSL is installed and available"""
        try:
            result = subprocess.run(
                ['wsl', '--list', '--quiet'],
                capture_output=True,
                text=True,
                check=True
            )
            if not result.stdout.strip():
                raise RuntimeError("No WSL distributions found. Please install WSL first.")
        except subprocess.CalledProcessError:
            raise RuntimeError("WSL is not installed. Please install Windows Subsystem for Linux first.")
        except FileNotFoundError:
            raise RuntimeError("WSL command not found. Please install Windows Subsystem for Linux first.")

    def _setup_wsl_environment(self) -> None:
        """Set up the WSL environment with required packages"""
        wsl_command = ['wsl']
        if self.wsl_distro:
            wsl_command.extend(['-d', self.wsl_distro])

        # Check if Python3 is available in WSL
        try:
            result = subprocess.run(
                wsl_command + ['which', 'python3'],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError:
            raise RuntimeError("Python3 not found in WSL. Please install Python3 in your WSL distribution.")

        # Check if prophet is installed in WSL
        try:
            result = subprocess.run(
                wsl_command + ['python3', '-c', 'import prophet; print("Prophet available")'],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError:
            logger.warning("Prophet not found in WSL. Installing...")
            self._install_prophet_in_wsl()

        # Create the prophet runner script in WSL
        self._create_prophet_runner_script()

    def _install_prophet_in_wsl(self) -> None:
        """Install Prophet and dependencies in WSL"""
        wsl_command = ['wsl']
        if self.wsl_distro:
            wsl_command.extend(['-d', self.wsl_distro])

        install_commands = [
            'python3 -m pip install --upgrade pip --break-system-packages',
            'python3 -m pip install prophet pandas numpy matplotlib --break-system-packages',
        ]

        for cmd in install_commands:
            logger.info(f"Running in WSL: {cmd}")
            result = subprocess.run(
                wsl_command + ['bash', '-c', cmd],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"WSL output: {result.stdout}")

    def _create_prophet_runner_script(self) -> None:
        """Create the Python script that will run in WSL"""
        script_content = '''
#!/usr/bin/env python3
"""
Prophet Runner Script for WSL
This script runs inside WSL and executes Prophet models
"""

import sys
import json
import pandas as pd
import numpy as np
from prophet import Prophet
import pickle
import base64
import io

def main():
    """Main function to run Prophet model"""
    try:
        # Read input from stdin
        input_data = sys.stdin.read()
        config = json.loads(input_data)

        # Extract parameters
        df_data = config['dataframe']
        model_params = config.get('model_params', {})
        forecast_periods = config.get('forecast_periods', 30)
        regressors = config.get('regressors', [])

        # Convert dataframe
        df = pd.DataFrame(df_data)
        df['ds'] = pd.to_datetime(df['ds'])

        # Initialize and fit model
        model = Prophet(**model_params)

        # Add regressors if specified
        for regressor in regressors:
            if regressor in df.columns:
                model.add_regressor(regressor)

        model.fit(df)

        # Make forecast
        future = model.make_future_dataframe(periods=forecast_periods)

        # Set cap and floor for logistic growth if they exist in training data
        if 'cap' in df.columns:
            future['cap'] = df['cap'].iloc[0]  # Use the same cap value
        if 'floor' in df.columns:
            future['floor'] = df['floor'].iloc[0]  # Use the same floor value

        # Set future regressor values
        for regressor in regressors:
            if regressor in df.columns:
                if len(df) >= 7:
                    future[regressor] = df[regressor].iloc[-7:].mean()
                else:
                    future[regressor] = df[regressor].iloc[-1]

        forecast = model.predict(future)

        # Prepare output
        output = {
            'success': True,
            'forecast': forecast.to_dict('records'),
            'model_info': {
                'params': model.params,
                'changepoints': model.changepoints.tolist() if model.changepoints is not None else None,
            }
        }

        # Convert Timestamps to ISO strings for JSON serialization
        for row in output['forecast']:
            for key, value in row.items():
                if hasattr(value, 'isoformat'):  # pandas Timestamp
                    row[key] = value.isoformat()

        if output['model_info']['changepoints']:
            output['model_info']['changepoints'] = [cp.isoformat() if hasattr(cp, 'isoformat') else str(cp) for cp in output['model_info']['changepoints']]

        # Convert numpy arrays to lists for JSON serialization
        if output['model_info']['params']:
            for key, value in output['model_info']['params'].items():
                if isinstance(value, np.ndarray):
                    output['model_info']['params'][key] = value.tolist()

        # Serialize model for potential future use
        model_buffer = io.BytesIO()
        pickle.dump(model, model_buffer)
        model_bytes = model_buffer.getvalue()
        output['model_pickle'] = base64.b64encode(model_bytes).decode('utf-8')

        print(json.dumps(output))

    except Exception as e:
        error_output = {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }
        print(json.dumps(error_output))

if __name__ == "__main__":
    main()
'''

        # Write script to WSL temp directory
        wsl_command = ['wsl']
        if self.wsl_distro:
            wsl_command.extend(['-d', self.wsl_distro])

        # Create temp file in WSL
        result = subprocess.run(
            wsl_command + ['mktemp'],
            capture_output=True,
            text=True,
            check=True
        )
        temp_path = result.stdout.strip()

        # Write script content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            local_script_path = f.name

        # Copy script to WSL
        with open(local_script_path, 'r') as f:
            script_content = f.read()

        result = subprocess.run(
            wsl_command + ['tee', temp_path],
            input=script_content,
            text=True,
            capture_output=True,
            check=True
        )

        # Make script executable
        subprocess.run(
            wsl_command + ['chmod', '+x', temp_path],
            check=True
        )

        self.prophet_script_path = temp_path

        # Clean up local temp file
        os.unlink(local_script_path)

    def fit_predict(self,
                   df: pd.DataFrame,
                   model_params: Dict[str, Any] = None,
                   forecast_periods: int = 30,
                   regressors: List[str] = None) -> Tuple[pd.DataFrame, Any]:
        """
        Fit Prophet model and generate forecast using WSL

        Args:
            df: DataFrame with 'ds' (datetime) and 'y' (target) columns
            model_params: Parameters for Prophet model
            forecast_periods: Number of periods to forecast
            regressors: List of column names to add as regressors

        Returns:
            Tuple of (forecast_df, model_info)
        """
        if model_params is None:
            model_params = {}
        if regressors is None:
            regressors = []

        # Prepare input data
        input_config = {
            'dataframe': df.to_dict('records'),
            'model_params': model_params,
            'forecast_periods': forecast_periods,
            'regressors': regressors
        }

        # Convert Timestamps to strings for JSON serialization
        for row in input_config['dataframe']:
            for key, value in row.items():
                if hasattr(value, 'isoformat'):  # pandas Timestamp
                    row[key] = value.isoformat()

        # Run in WSL
        wsl_command = ['wsl']
        if self.wsl_distro:
            wsl_command.extend(['-d', self.wsl_distro])

        result = subprocess.run(
            wsl_command + ['python3', self.prophet_script_path],
            input=json.dumps(input_config),
            capture_output=True,
            text=True,
            check=True
        )

        # Parse output
        output = json.loads(result.stdout)

        if not output['success']:
            raise RuntimeError(f"WSL Prophet failed: {output['error']}")

        # Convert forecast back to DataFrame
        forecast_df = pd.DataFrame(output['forecast'])
        forecast_df['ds'] = pd.to_datetime(forecast_df['ds'])

        return forecast_df, output['model_info']

def create_wsl_prophet_bridge(wsl_distro: str = None) -> WSLProphetBridge:
    """
    Factory function to create WSL Prophet Bridge

    Args:
        wsl_distro: WSL distribution name

    Returns:
        WSLProphetBridge instance
    """
    return WSLProphetBridge(wsl_distro)

# Compatibility function that mimics the original prophet interface
def train_prophet_model(df: pd.DataFrame,
                       model_params: Dict[str, Any] = None,
                       forecast_periods: int = 30,
                       regressors: List[str] = None) -> Tuple[Any, pd.DataFrame, pd.DataFrame]:
    """
    Train Prophet model using WSL bridge (compatible with existing code)

    Args:
        df: Input dataframe with 'ds' and 'y' columns
        model_params: Prophet model parameters
        forecast_periods: Periods to forecast
        regressors: List of regressor column names

    Returns:
        Tuple of (model, forecast_df, actual_df) - model is None for WSL bridge
    """
    try:
        bridge = create_wsl_prophet_bridge()
        forecast_df, model_info = bridge.fit_predict(df, model_params, forecast_periods, regressors)

        # Return format compatible with existing code
        return None, forecast_df, df

    except Exception as e:
        logger.error(f"WSL Prophet training failed: {e}")
        raise

if __name__ == "__main__":
    # Test the bridge
    print("Testing WSL Prophet Bridge...")

    # Create test data
    dates = pd.date_range('2020-01-01', periods=365, freq='D')
    values = np.sin(np.arange(365) * 2 * np.pi / 365) * 10 + np.random.normal(0, 1, 365) + 100

    df = pd.DataFrame({
        'ds': dates,
        'y': values
    })

    try:
        model, forecast, actual = train_prophet_model(df)
        print("✅ WSL Prophet Bridge test successful!")
        print(f"   - Forecast shape: {forecast.shape}")
    except Exception as e:
        print(f"❌ WSL Prophet Bridge test failed: {e}")
        sys.exit(1)