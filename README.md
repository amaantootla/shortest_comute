# Commute Optimizer

## Overview

This project is a Python-based tool designed to find the optimal departure time to minimize your total daily commute. It analyzes various departure times by fetching real-time and predictive traffic data to calculate the total round-trip travel time (morning and evening commutes), identifying the best window to leave for work.

The script is highly flexible, allowing users to select from different mapping and geocoding APIs, including Google Maps, TomTom, and a cost-saving fallback mechanism that uses Geocode.co for address lookups.

## Features

* **Dynamic Commute Analysis:** Simulates morning and evening commutes for a range of departure times to find the one with the shortest total travel duration, based on traffic data.
* **Multiple API Support:** Integrates with Google Maps, TomTom, and Geocode.co.
* **Cost-Saving Fallback:** Can use the free Geocode.co service for address lookups and then fall back to Google Maps or TomTom for routing, which can help reduce API costs.
* **User-Friendly and Configurable:** Users can easily input their home and work addresses, and specify their typical lunch break duration.
* **Clear and Actionable Results:** Presents a detailed breakdown of each simulated scenario in a clean table and highlights the best departure time with the minimum total commute.
* **Intelligent Rate Limiting:** Includes built-in delays to avoid overwhelming the APIs with too many requests in a short period.

## How It Works

The script operates through a series of modular components:

1.  **`commute_optimizer.py` (Main Script):** This is the user-facing script that orchestrates the entire process. It handles user input for addresses, API selection, and lunch duration. It then iterates through a predefined time window (e.g., 6:00 AM to 10:00 AM), calculating the full commute cycle for each departure time.

2.  **`api_adapters.py` (API Integration):** This module contains the logic for interacting with external mapping services. It uses an **Adapter** design pattern, where each service (Google Maps, TomTom, Geocode.co) has its own class that conforms to a common `ApiAdapter` interface. This makes it easy to switch between services or add new ones in the future. It also includes a `FallbackGeocoderAdapter` that intelligently combines a geocoding-only service with a full-featured routing service.

3.  **`api_structures.py` (Data Structures):** This file defines standardized data classes (`Coordinates` and `RouteInfo`) used throughout the application. This ensures that data received from different APIs is normalized into a consistent internal format, decoupling the main logic from the specifics of any single API's response structure.

#### The core logic flow is as follows:
* The user provides their home and work addresses at the command line.
* The selected API adapter geocodes these addresses into latitude and longitude coordinates.
* The script then simulates departures every 30 minutes within a set morning period.
* For each departure time:
    * It calculates the morning travel time to work, including traffic.
    * It determines the corresponding work departure time (assuming an 8-hour workday plus the specified lunch break).
    * It calculates the evening travel time back home.
    * The morning and evening travel times are summed to get the total commute time for that scenario.
* Finally, all scenarios are displayed in a table, and the one with the lowest total commute time is presented as the recommended option.

## Setup & Usage

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/commute-optimizer.git](https://github.com/your-username/commute-optimizer.git)
    cd commute-optimizer
    ```

2.  **Install dependencies:**
    This project uses `requests` to make API calls and `python-dotenv` to manage environment variables. Install them using pip:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your API Keys:**
    You will need API keys for the mapping services you intend to use. Create a file named `.env` in the root of the project directory and add your keys like so:

    ```
    # .env
    GOOGLE_API_KEY="YOUR_GOOGLE_MAPS_API_KEY"
    TOMTOM_API_KEY="YOUR_TOMTOM_API_KEY"
    GEOCODECO_API_KEY="YOUR_GEOCODE.CO_API_KEY"
    COMMUTE_TZ="America/Los_Angeles"
    ```
    *Note: You only need to provide keys for the services you plan to use.*

4.  **Run the script:**
    Execute the main script from your terminal:
    ```bash
    python commute_optimizer.py
    ```

5.  **Follow the prompts:**
    The script will guide you through selecting an API service and entering your commute details. Default values are provided for convenience.

    You can also run the script with the `--verbose` flag to see detailed information about the API calls being made:
    ```bash
    python commute_optimizer.py --verbose
    ```

## Configuration

### Environment Variables

The following variables can be set in your `.env` file:

* **`GOOGLE_API_KEY`**: Your API key for the Google Maps Platform. Required if you select any Google Maps option.
* **`TOMTOM_API_KEY`**: Your API key for the TomTom Developer Portal. Required if you select any TomTom option.
* **`GEOCODECO_API_KEY`**: Your API key for Geocode.co. This is a free service often used in the fallback options to save on paid geocoding calls.
* **`COMMUTE_TZ`**: The IANA timezone name for your commute (e.g., `America/New_York`, `Europe/London`). Defaults to `America/Los_Angeles` if not set.
