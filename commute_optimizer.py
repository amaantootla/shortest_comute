# commute_optimizer.py
# Main script to analyze and optimize daily commute times.

import time
from datetime import datetime, timedelta, date

# Import the adapter blueprint and the specific implementation we want to use
from api_adapters import ApiAdapter, TomTomAdapter

# --- Helper Functions (Not API-specific) ---


def get_next_weekday() -> date:
    """Calculates the date of the next upcoming weekday."""
    today = date.today()
    # If it's Friday (4), add 3 days to get to Monday
    if today.weekday() == 4:
        return today + timedelta(days=3)
    # If it's Saturday (5), add 2 days to get to Monday
    elif today.weekday() == 5:
        return today + timedelta(days=2)
    # Otherwise (Sunday-Thursday), just go to the next day
    else:
        return today + timedelta(days=1)


def format_duration(seconds: int) -> str:
    """Converts seconds into a readable 'XX min' format."""
    return f"{round(seconds / 60)} min"


# --- Core Logic (Now API-agnostic) ---

def analyze_commute_scenarios(
    home_address: str,
    work_address: str,
    analysis_date: date,
    lunch_minutes: int,
    api_adapter: ApiAdapter  # Expects an adapter object
):
    """
    Analyzes multiple departure times using the provided API adapter.
    """
    print("\n--- Starting Commute Analysis ---")

    # 1. Get coordinates using the provided adapter
    home_coords = api_adapter.get_coordinates(home_address)
    work_coords = api_adapter.get_coordinates(work_address)
    if not home_coords or not work_coords:
        print("\nCould not proceed without valid coordinates for both addresses.")
        return []

    # 2. Define the time range for the analysis (6:00 AM to 10:00 AM)
    scenarios = []
    start_hour = 6
    end_hour = 10
    increment_minutes = 30
    current_time = datetime(
        analysis_date.year, analysis_date.month, analysis_date.day, start_hour)
    end_time = current_time.replace(hour=end_hour)

    print(
        f"\nAnalyzing departures for {analysis_date.strftime('%A, %B %d, %Y')}")
    print("This will take a few moments as we make multiple API calls...\n")

    # 3. Loop through each departure time and run the simulation
    while current_time <= end_time:
        departure_str = current_time.strftime('%I:%M %p')
        print(f"--- Analyzing departure at {departure_str} ---")
        time.sleep(0.5)  # A small delay to avoid hitting API rate limits

        # --- MORNING TRIP ---
        morning_route_info = api_adapter.get_route(
            home_coords, work_coords, current_time)
        if not morning_route_info:
            current_time += timedelta(minutes=increment_minutes)
            continue  # Skip this time slot if morning route fails

        morning_travel_seconds = morning_route_info.travel_time_sec
        work_arrival_time = current_time + \
            timedelta(seconds=morning_travel_seconds)
        work_departure_time = work_arrival_time + \
            timedelta(hours=8, minutes=lunch_minutes)

        # --- EVENING TRIP ---
        evening_route_info = api_adapter.get_route(
            work_coords, home_coords, work_departure_time)
        if not evening_route_info:
            current_time += timedelta(minutes=increment_minutes)
            continue  # Skip this time slot if evening route fails

        evening_travel_seconds = evening_route_info.travel_time_sec

        # --- STORE RESULTS ---
        scenarios.append({
            'leave_home': current_time,
            'morning_travel_sec': morning_travel_seconds,
            'arrive_work': work_arrival_time,
            'leave_work': work_departure_time,
            'evening_travel_sec': evening_travel_seconds,
            'total_commute_sec': morning_travel_seconds + evening_travel_seconds,
        })

        current_time += timedelta(minutes=increment_minutes)

    return scenarios


def display_results(scenarios: list, analysis_date: date):
    """Formats and prints the results table and the final recommendation."""
    if not scenarios:
        print("\nAnalysis could not be completed. No scenarios were generated.")
        return

    print("\n--- Commute Analysis Results ---")
    print(f"Scenarios for {analysis_date.strftime('%A, %B %d, %Y')}\n")

    header = "| Leave Home | Morning Trip | Arrive Work | Leave Work | Evening Trip | Total Commute |"
    divider = "-" * len(header)
    print(header)
    print(divider)

    for s in scenarios:
        print(f"| {s['leave_home'].strftime('%I:%M %p'):<10} | "
              f"{format_duration(s['morning_travel_sec']):<12} | "
              f"{s['arrive_work'].strftime('%I:%M %p'):<11} | "
              f"{s['leave_work'].strftime('%I:%M %p'):<10} | "
              f"{format_duration(s['evening_travel_sec']):<12} | "
              f"**{format_duration(s['total_commute_sec']):<11}** |")

    print(divider)

    best_scenario = min(scenarios, key=lambda x: x['total_commute_sec'])
    best_leave_time = best_scenario['leave_home'].strftime('%I:%M %p')
    min_total_time = format_duration(best_scenario['total_commute_sec'])

    print("\n✨ Best Option Found ✨")
    print(f"To minimize your total time on the road ({min_total_time}), "
          f"leave for work at {best_leave_time}.")


# --- Main Execution Block ---

if __name__ == '__main__':
    print("--- Daily Commute Optimizer ---")
    print("This tool will test multiple departure times to find the one that")
    print("minimizes your total daily commute time (morning + evening).\n")

    try:
        # 1. CHOOSE AND CREATE THE ADAPTER TO USE
        # To switch to a different API, you would just change this one line.
        selected_api_adapter = TomTomAdapter()
    except ValueError as e:
        print(e)
        exit()

    # 2. Get user inputs
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

    # 3. Determine the analysis date and run the simulation
    commute_date = get_next_weekday()
    all_scenarios = analyze_commute_scenarios(
        home, work, commute_date, lunch, selected_api_adapter)

    # 4. Display the final report
    display_results(all_scenarios, commute_date)
