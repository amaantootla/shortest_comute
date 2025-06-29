# Main script to analyze and optimize daily commute times.

import time
import os
import argparse
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from api_adapters import ApiAdapter, TomTomAdapter, GoogleMapsAdapter


def get_next_weekday() -> date:
    """Calculates the date of the next upcoming weekday."""
    today = date.today()
    # If it's Friday (4), add 3 days to get to Monday.
    if today.weekday() == 4:
        return today + timedelta(days=3)
    # If it's Saturday (5), add 2 days to get to Monday.
    elif today.weekday() == 5:
        return today + timedelta(days=2)
    # Otherwise (Sunday-Thursday), just go to the next day.
    else:
        return today + timedelta(days=1)


def format_duration(seconds: int, traffic_ok: bool) -> str:
    """Converts seconds into a readable 'XX min' format, noting if traffic data was missing."""
    duration_str = f"{round(seconds / 60)} min"
    if not traffic_ok:
        return f"{duration_str}*"
    return duration_str


# --- Core Logic ---

def analyze_commute_scenarios(
    home_address: str,
    work_address: str,
    analysis_date: date,
    lunch_minutes: int,
    api_adapter: ApiAdapter
):
    """
    Analyzes multiple departure times using the provided API adapter.
    """
    print("\nStarting commute analysis.")

    home_coords = api_adapter.get_coordinates(home_address)
    work_coords = api_adapter.get_coordinates(work_address)
    if not home_coords or not work_coords:
        print("\nCould not proceed without valid coordinates for both addresses.")
        return []

    # Define the time range for the analysis (6:00 AM to 10:00 AM).
    scenarios = []
    start_hour = 6
    end_hour = 10
    increment_minutes = 30
    naive_start_time = datetime(
        analysis_date.year, analysis_date.month, analysis_date.day, start_hour)
    current_time = naive_start_time.replace(tzinfo=COMMUTE_TZ)

    end_time = current_time.replace(hour=end_hour)

    print(
        f"\nAnalyzing departures for {analysis_date.strftime('%A, %B %d, %Y')}")
    print("This will take a few moments as we make multiple API calls...\n")

    # Loop through each departure time and run the simulation.
    while current_time <= end_time:
        departure_str = current_time.strftime('%I:%M %p')
        print(f"Analyzing departure at {departure_str}.")

        time.sleep(0.5)  # A small delay to avoid hitting API rate limits.

        morning_route_info = api_adapter.get_route(
            home_coords, work_coords, current_time)
        if not morning_route_info:
            print(
                f"   ! Skipping {departure_str}: Could not calculate the morning route.")
            current_time += timedelta(minutes=increment_minutes)
            continue

        morning_travel_seconds = morning_route_info.travel_time_sec
        work_arrival_time = current_time + \
            timedelta(seconds=morning_travel_seconds)
        work_departure_time = work_arrival_time + \
            timedelta(hours=8, minutes=lunch_minutes)

        evening_route_info = api_adapter.get_route(
            work_coords, home_coords, work_departure_time)
        if not evening_route_info:
            evening_departure_str = work_departure_time.strftime('%I:%M %p')
            print(
                f"   ! Skipping {departure_str} departure: Could not calculate the evening route (leaving work at {evening_departure_str}).")
            current_time += timedelta(minutes=increment_minutes)
            continue

        evening_travel_seconds = evening_route_info.travel_time_sec

        scenarios.append({
            'leave_home': current_time,
            'morning_travel_sec': morning_travel_seconds,
            'morning_traffic_ok': morning_route_info.traffic_data_included,
            'arrive_work': work_arrival_time,
            'leave_work': work_departure_time,
            'evening_travel_sec': evening_travel_seconds,
            'evening_traffic_ok': evening_route_info.traffic_data_included,
            'total_commute_sec': morning_travel_seconds + evening_travel_seconds,
        })

        current_time += timedelta(minutes=increment_minutes)

    return scenarios


def display_results(scenarios: list, analysis_date: date):
    """Formats and prints the results table and the final recommendation."""
    if not scenarios:
        print("\nAnalysis could not be completed. No scenarios were generated.")
        return

    print("\nHere are the commute analysis results.")
    print(f"Scenarios for {analysis_date.strftime('%A, %B %d, %Y')}\n")

    # Check if any scenario is missing traffic data to decide if we need to print the footnote.
    any_missing_traffic = any(
        not s['morning_traffic_ok'] or not s['evening_traffic_ok'] for s in scenarios)
    if any_missing_traffic:
        print("NOTE: An asterisk (*) indicates the travel time was calculated without live traffic data.\n")

    header = "| Leave Home | Morning Trip | Arrive Work | Leave Work | Evening Trip | Total Commute |"
    divider = "-" * len(header)
    print(header)
    print(divider)

    for s in scenarios:
        total_commute_traffic_ok = s['morning_traffic_ok'] and s['evening_traffic_ok']
        print(f"| {s['leave_home'].strftime('%I:%M %p'):<10} | "
              f"{format_duration(s['morning_travel_sec'], s['morning_traffic_ok']):<12} | "
              f"{s['arrive_work'].strftime('%I:%M %p'):<11} | "
              f"{s['leave_work'].strftime('%I:%M %p'):<10} | "
              f"{format_duration(s['evening_travel_sec'], s['evening_traffic_ok']):<12} | "
              f"**{format_duration(s['total_commute_sec'], total_commute_traffic_ok):<11}** |")

    print(divider)

    best_scenario = min(scenarios, key=lambda x: x['total_commute_sec'])
    best_leave_time = best_scenario['leave_home'].strftime('%I:%M %p')

    # For the final recommendation, ensure the traffic flag is passed to the formatter
    best_total_traffic_ok = best_scenario['morning_traffic_ok'] and best_scenario['evening_traffic_ok']
    min_total_time = format_duration(
        best_scenario['total_commute_sec'], best_total_traffic_ok)

    print("\n✨ Best Option Found ✨")
    print(f"To minimize your total time on the road ({min_total_time}), "
          f"leave for work at {best_leave_time}.")


if __name__ == '__main__':
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Daily Commute Optimizer: Find the best departure time.")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Enable verbose mode to see the exact API calls being made.")
    args = parser.parse_args()

    print("Welcome to the Daily Commute Optimizer.")
    print("This tool tests multiple departure times to find the one that")
    print("minimizes your total daily commute time (morning + evening).\n")

    print("Select the mapping API to use:")
    print("1. Google Maps (Default)")
    print("2. TomTom")
    api_choice = input("Enter your choice [1]: ") or "1"

    selected_api_adapter = None
    try:
        if api_choice == '2':
            print("Using TomTom API.\n")
            selected_api_adapter = TomTomAdapter(verbose=args.verbose)
        else:
            if api_choice != '1':
                print("Invalid choice. Using Google Maps API by default.\n")
            else:
                print("Using Google Maps API.\n")
            selected_api_adapter = GoogleMapsAdapter(verbose=args.verbose)

    except ValueError as e:
        print(e)
        exit()

    COMMUTE_TIMEZONE_STR = os.getenv("COMMUTE_TZ", "America/Los_Angeles")
    try:
        COMMUTE_TZ = ZoneInfo(COMMUTE_TIMEZONE_STR)
    except Exception:
        print(
            f"FATAL ERROR: The timezone '{COMMUTE_TIMEZONE_STR}' set in the COMMUTE_TZ environment variable is invalid.")
        print("Please use a valid IANA timezone name (e.g., 'America/New_York', 'Europe/London').")
        exit()
    finally:
        print(f"Using timezone: {COMMUTE_TZ.key}")

    home = input(
        "Enter your Home Address [Default: 1 Rocket Road, Hawthorne, CA]: ") or "1 Rocket Road, Hawthorne, CA"
    work = input(
        "Enter your Work Address [Default: 2600 Alton Pkwy, Irvine, CA]: ") or "2600 Alton Pkwy, Irvine, CA"

    while True:
        lunch_input = input(
            "Enter your lunch break in minutes [Default: 30]: ") or "30"
        try:
            lunch = int(lunch_input)
            if lunch < 0:
                print("Please enter a positive number.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    commute_date = get_next_weekday()
    all_scenarios = analyze_commute_scenarios(
        home, work, commute_date, lunch, selected_api_adapter)

    display_results(all_scenarios, commute_date)
