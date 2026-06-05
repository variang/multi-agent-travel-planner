"""Custom OpenWeatherMap tool functions used by the weather agent."""

import re
import calendar
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import os
import requests
from dateutil import parser as date_parser


def parse_flexible_date_range(date_str: str) -> Optional[tuple]:
    """
    Parses a wide variety of date expressions and returns (start_date, end_date).

    Supports:
    - 'today', 'tomorrow', 'in 3 days'
    - 'this weekend', 'next weekend'
    - 'next week', 'this week', 'last week'
    - 'first week of July', 'second week of August', etc.
    - Specific dates: '2025-07-01', 'July 1', '07-01'
    - Date ranges: 'July 1 to July 5', 'next 3 days'

    Returns (datetime, datetime) or None if parsing fails.
    """
    date_str = date_str.lower().strip()
    today = datetime.today()
    weekday = today.weekday()  # Monday=0, Sunday=6

    target_date = None
    if date_str in ["today", "now"]:
        target_date = today
    elif date_str == "tomorrow":
        target_date = today + timedelta(days=1)

    match = re.match(r"in (\d+) days?", date_str)
    if match:
        days = int(match.group(1))
        target_date = today + timedelta(days=days)

    if target_date:
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start_of_day, end_of_day

    match = re.match(r"(?:next|for the next) (\d+) days?", date_str)
    if match:
        days = int(match.group(1))
        start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end = today + timedelta(days=days - 1)
        end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end

    if date_str == "this week":
        start = today - timedelta(days=weekday)
        end = start + timedelta(days=6)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end

    if date_str == "next week":
        start = today - timedelta(days=weekday) + timedelta(days=7)
        end = start + timedelta(days=6)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end

    if date_str == "last week":
        start = today - timedelta(days=weekday) - timedelta(days=7)
        end = start + timedelta(days=6)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end

    if date_str == "this weekend":
        saturday = today + timedelta((5 - weekday) % 7)
        sunday = saturday + timedelta(days=1)
        saturday = saturday.replace(hour=0, minute=0, second=0, microsecond=0)
        sunday = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
        return saturday, sunday

    if date_str == "next weekend":
        saturday = today + timedelta((5 - weekday) % 7 + 7)
        sunday = saturday + timedelta(days=1)
        saturday = saturday.replace(hour=0, minute=0, second=0, microsecond=0)
        sunday = sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
        return saturday, sunday

    match = re.match(r"(first|second|third|fourth|last) week of (\w+)", date_str)
    if match:
        week_map = {"first": 0, "second": 1, "third": 2, "fourth": 3, "last": -1}
        week_num = week_map[match.group(1)]
        month_str = match.group(2)
        try:
            month = list(calendar.month_name).index(month_str.capitalize())
            year = today.year
            if month < today.month:
                year += 1
            cal = calendar.monthcalendar(year, month)
            week = cal[-1] if week_num == -1 else (cal[week_num] if week_num < len(cal) else None)
            if week is None:
                return None
            days_in_week = [d for d in week if d != 0]
            if days_in_week:
                start = datetime(year, month, days_in_week[0]).replace(hour=0, minute=0, second=0, microsecond=0)
                end = datetime(year, month, days_in_week[-1]).replace(hour=23, minute=59, second=59, microsecond=999999)
                return start, end
        except (ValueError, Exception):
            return None

    try:
        dt = date_parser.parse(date_str, fuzzy=True, default=today)
        start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end
    except Exception:
        pass

    if " to " in date_str:
        parts = date_str.split(" to ")
        try:
            start = date_parser.parse(parts[0], fuzzy=True, default=today).replace(hour=0, minute=0, second=0, microsecond=0)
            end = date_parser.parse(parts[1], fuzzy=True, default=today).replace(hour=23, minute=59, second=59, microsecond=999999)
            return start, end
        except Exception:
            return None

    return None


def get_current_weather_from_openweather_stateful(city: Optional[str], tool_context) -> Dict[str, Any]:
    """
    Retrieves current weather for a city from OpenWeatherMap.
    Reads/writes last_city_checked_stateful and user_preference_temperature_unit from session state.
    """
    OPEN_WEATHER_API_KEY = os.environ.get("OPEN_WEATHER_API_KEY", "")
    preferred_unit = tool_context.state.get("user_preference_temperature_unit", "metric")
    unit_symbol = "°C" if preferred_unit == "metric" else "°F"

    if not city:
        city = tool_context.state.get("last_city_checked_stateful")
        if not city:
            return {"status": "error", "error_message": "No city specified or remembered. Please provide a city."}

    print(f"--- Tool: get_current_weather called for city: {city}, unit: {preferred_unit} ---")
    response_data: Dict[str, Any] = {}
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPEN_WEATHER_API_KEY}&units={preferred_unit}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data["cod"] == 200:
            desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            feels = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            wind = data["wind"]["speed"]
            report = (
                f"The current weather in {city} is {desc} with a temperature of {temp}{unit_symbol} "
                f"(feels like {feels}{unit_symbol}). Humidity is {humidity}% and wind speed is {wind} m/s."
            )
            response_data = {"status": "success", "report": report}
        else:
            response_data = {"status": "error", "error_message": f"API error: {data.get('message', 'Unknown')}"}
    except requests.exceptions.Timeout:
        response_data = {"status": "error", "error_message": f"Request timed out for {city}."}
    except requests.exceptions.RequestException as e:
        response_data = {"status": "error", "error_message": f"Error fetching weather for {city}: {e}"}
    except (KeyError, Exception) as e:
        response_data = {"status": "error", "error_message": f"Unexpected error for {city}: {e}"}

    if city:
        tool_context.state["last_city_checked_stateful"] = city
    return response_data


def get_weather_summary_from_openweather_stateful(
    city: Optional[str], date_expr: Optional[str], tool_context
) -> Dict[str, Any]:
    """
    Summarizes the weather forecast for a city and flexible date expression.
    Reads/writes last_city_checked_stateful, last_date_expr_stateful, and
    user_preference_temperature_unit from session state.
    """
    OPEN_WEATHER_API_KEY = os.environ.get("OPEN_WEATHER_API_KEY", "")

    if not city:
        city = tool_context.state.get("last_city_checked_stateful")
    if not city:
        return {"status": "error", "error_message": "No city specified or remembered. Please provide a city."}

    if not date_expr:
        date_expr = tool_context.state.get("last_date_expr_stateful")
    if not date_expr:
        return {"status": "error", "error_message": "No date expression specified or remembered."}

    preferred_unit = tool_context.state.get("user_preference_temperature_unit", "metric")
    unit_symbol = "°C" if preferred_unit == "metric" else "°F"

    print(f"--- Tool: get_weather_summary called for city: {city}, date_expr: {date_expr}, unit: {preferred_unit} ---")
    response_data: Dict[str, Any] = {}
    try:
        date_range = parse_flexible_date_range(date_expr)
        if not date_range:
            return {"status": "error", "error_message": f"Could not parse date expression: '{date_expr}'."}

        start, end = date_range
        current_utc = datetime.now(timezone.utc).date()
        forecast_limit = 5

        if end.date() < current_utc:
            response_data = {"status": "info", "report": f"'{date_expr}' appears to be in the past. Please specify a future date."}
        elif (start.date() - current_utc).days > forecast_limit:
            response_data = {"status": "info", "report": f"I can only forecast up to {forecast_limit} days. '{date_expr}' is too far in the future."}
        else:
            url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={OPEN_WEATHER_API_KEY}&units={preferred_unit}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data["cod"] != "200":
                response_data = {"status": "error", "error_message": f"API error: {data.get('message', 'Unknown')}"}
            else:
                all_temps = []
                all_descs = []
                for entry in data.get("list", []):
                    entry_dt = datetime.fromtimestamp(entry["dt"]).replace(tzinfo=None)
                    if start <= entry_dt <= end:
                        all_temps.append(entry["main"]["temp"])
                        all_descs.append(entry["weather"][0]["description"])

                if not all_temps:
                    response_data = {"status": "info", "report": f"No forecast entries found for {city} in '{date_expr}'."}
                else:
                    min_t = round(min(all_temps), 1)
                    max_t = round(max(all_temps), 1)
                    avg_t = round(sum(all_temps) / len(all_temps), 1)
                    top_descs = ", ".join(d for d, _ in Counter(all_descs).most_common(3))
                    city_name = data["city"]["name"]
                    report = (
                        f"Weather in {city_name} from {start.strftime('%B %d')} to {end.strftime('%B %d')}: "
                        f"generally {top_descs}, avg {avg_t}{unit_symbol}, range {min_t}–{max_t}{unit_symbol}."
                    )
                    response_data = {"status": "success", "summary": report}

    except requests.exceptions.Timeout:
        response_data = {"status": "error", "error_message": f"Request timed out for {city}."}
    except requests.exceptions.RequestException as e:
        response_data = {"status": "error", "error_message": f"Error fetching forecast for {city}: {e}"}
    except (KeyError, Exception) as e:
        response_data = {"status": "error", "error_message": f"Unexpected error for {city}: {e}"}

    if city:
        tool_context.state["last_city_checked_stateful"] = city
    if date_expr:
        tool_context.state["last_date_expr_stateful"] = date_expr
    return response_data
