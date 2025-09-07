import os
import googlemaps
import csv
import io
from flask import Flask, render_template, request
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Securely get the API key from the environment
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_MAPS_API_KEY not set in .env file")

# Initialize the Google Maps client
gmaps = googlemaps.Client(key=API_KEY)

@app.route('/', methods=['GET', 'POST'])
def index():
    context = {}
    if request.method == 'POST':
        try:
            # 1. GET THE STARTING POINT
            lat = request.form.get('latitude')
            lon = request.form.get('longitude')
            # Prioritize detected location over manual input
            if lat and lon:
                start_location = f"{lat},{lon}"
            else:
                start_location = request.form.get('start_point', '').strip()

            # 2. GET DESTINATIONS (from CSV or Text Area)
            destinations = []
            if 'csv_file' in request.files and request.files['csv_file'].filename != '':
                csv_file = request.files['csv_file']
                # Read the CSV file in memory
                decoded_file = csv_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                # Assume addresses are in the first column
                for row in csv.reader(io_string):
                    if row and row[0].strip():
                        destinations.append(row[0].strip())
            else:
                addresses_text = request.form.get('addresses', '').strip()
                if addresses_text:
                    destinations = [addr.strip() for addr in addresses_text.split(';') if addr.strip()]

            # 3. VALIDATE INPUT
            if not start_location or not destinations:
                context['error'] = "Please provide a starting point and at least one destination."
                return render_template('index.html', **context)

            # 4. CALL GOOGLE MAPS API
            matrix = gmaps.distance_matrix(start_location, destinations, mode="driving")

            # 5. PROCESS AND SORT RESULTS
            results = []
            for i, element in enumerate(matrix['rows'][0]['elements']):
                if element['status'] == 'OK':
                    results.append({
                        'address': destinations[i],
                        'distance_text': element['distance']['text'],
                        'distance_value': element['distance']['value'], # in meters
                        'duration_text': element['duration']['text']
                    })
                else:
                    results.append({'address': f"{destinations[i]} (Not found)", 'distance_value': float('inf')})

            context['sorted_destinations'] = sorted(results, key=lambda x: x['distance_value'])

            # 6. GENERATE OPTIMIZED GOOGLE MAPS URL
            valid_addresses = [d['address'] for d in context['sorted_destinations'] if d['distance_value'] != float('inf')]
            if valid_addresses:
                # The URL uses the last valid address as the final destination
                # and all others as waypoints, joined by a pipe character '|'
                maps_url = f"https://www.google.com/maps/dir/?api=1&origin={start_location}&destination={valid_addresses[-1]}&waypoints={'|'.join(valid_addresses[:-1])}"
                context['maps_url'] = maps_url

        except Exception as e:
            context['error'] = f"An unexpected error occurred: {e}"

        return render_template('index.html', **context)

    # For a GET request, just show the initial page
    return render_template('index.html')

if __name__ == '__main__':
    # This runs the app in development mode
    app.run(debug=True)