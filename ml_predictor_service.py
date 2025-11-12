import pandas as pd
import time
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

class MockLSTMPredictor:
    def __init__(self, dataset_path):
        self.df = pd.read_csv(dataset_path)
        # Convert timestamp strings to datetime
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.current_hour_index = 0
        self.hourly_timestamps = sorted(self.df['timestamp'].unique())
        self.total_hours = len(self.hourly_timestamps)
        
        print(f"Loaded {len(self.df)} records for {self.df['link_id'].nunique()} links")
        print(f"Time range: {self.hourly_timestamps[0]} to {self.hourly_timestamps[-1]}")
    
    def get_next_hour_predictions(self):
        """Get predictions for next hour for all links"""
        if self.total_hours == 0:
            return []
        
        # Get current hour timestamp
        current_timestamp = self.hourly_timestamps[self.current_hour_index]
        
        # Get all records for this hour
        hour_data = self.df[self.df['timestamp'] == current_timestamp]
        
        # Move to next hour (circular)
        self.current_hour_index = (self.current_hour_index + 1) % self.total_hours
        
        print(f"Sent predictions for {len(hour_data)} links at {current_timestamp}")
        return hour_data.to_dict('records')

# Initialize predictor
predictor = MockLSTMPredictor('5g_backhaul_traffic.csv')

@app.route('/predictions/next_hour', methods=['GET'])
def get_predictions():
    """Endpoint for Ryu controller to get next hour predictions"""
    try:
        predictions = predictor.get_next_hour_predictions()
        return jsonify({
            'timestamp': str(predictor.hourly_timestamps[predictor.current_hour_index]) if predictions else None,
            'predictions': predictions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'total_links': len(predictor.df['link_id'].unique())})

if __name__ == '__main__':
    print("Starting Mock LSTM Prediction Service on http://localhost:5000")
    print("Predictions will cycle through dataset hours every request")
    app.run(host='0.0.0.0', port=5000, debug=False)