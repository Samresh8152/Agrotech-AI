"""Weather for the farmer's saved city, summarised per day, plus simple rule-based field alerts."""
import os
from collections import Counter, defaultdict

import requests

OWM_URL = 'https://api.openweathermap.org/data/2.5'


def _key():
    return os.getenv('OPENWEATHER_API_KEY', 'bd5e378503939ddaee76f12ad7a97608')


class WeatherError(Exception):
    pass


def fetch(city):
    """Return (current, days) for a city. days = up to 5 daily summaries from the 3-hourly forecast."""
    params = {'q': city, 'appid': _key(), 'units': 'metric'}
    try:
        cur = requests.get(f'{OWM_URL}/weather', params=params, timeout=10)
        fc = requests.get(f'{OWM_URL}/forecast', params={**params, 'cnt': 40}, timeout=10)
    except requests.exceptions.RequestException:
        raise WeatherError('Could not reach the weather service. Check your internet connection.')
    if cur.status_code == 404:
        raise WeatherError(f'City "{city}" was not found. Try the nearest town or district name.')
    if cur.status_code != 200 or fc.status_code != 200:
        raise WeatherError('The weather service did not respond. Try again in a minute.')

    c = cur.json()
    current = {
        'city': c['name'],
        'country': c['sys']['country'],
        'temperature': round(c['main']['temp'], 1),
        'feels_like': round(c['main']['feels_like'], 1),
        'humidity': c['main']['humidity'],
        'description': c['weather'][0]['description'].capitalize(),
        'wind_speed': round(c['wind']['speed'] * 3.6, 1),
        'rainfall_1h': c.get('rain', {}).get('1h', 0),
        'clouds': c['clouds']['all'],
        'sunrise': c['sys']['sunrise'],
        'sunset': c['sys']['sunset'],
    }

    by_day = defaultdict(list)
    for item in fc.json()['list']:
        by_day[item['dt_txt'][:10]].append(item)
    days = []
    for d, items in sorted(by_day.items())[:5]:
        days.append({
            'date': d,
            'temp_min': round(min(i['main']['temp_min'] for i in items), 1),
            'temp_max': round(max(i['main']['temp_max'] for i in items), 1),
            'humidity': round(sum(i['main']['humidity'] for i in items) / len(items)),
            'rain_mm': round(sum(i.get('rain', {}).get('3h', 0) for i in items), 1),
            'rain_chance': round(max(i.get('pop', 0) for i in items) * 100),
            'wind_max': round(max(i['wind']['speed'] for i in items) * 3.6, 1),
            'description': Counter(i['weather'][0]['description'] for i in items).most_common(1)[0][0].capitalize(),
        })
    return current, days


def field_alerts(current, days, crops):
    """Plain-language advice from the next few days of weather and the crops in the field."""
    alerts = []
    if not days:
        return alerts
    growing = [c.crop for c in crops if c.status == 'growing']
    crop_txt = ', '.join(sorted(set(growing))) if growing else 'your crops'
    next2 = days[:2]
    rain_2d = sum(d['rain_mm'] for d in next2)
    rain_5d = sum(d['rain_mm'] for d in days)
    hottest = max(d['temp_max'] for d in days)
    coldest = min(d['temp_min'] for d in days)
    windiest = max(d['wind_max'] for d in next2)
    humid_days = [d for d in next2 if d['humidity'] >= 80 and 15 <= d['temp_max'] <= 32]

    if rain_2d >= 5:
        alerts.append({'level': 'info', 'title': f'Rain expected: about {rain_2d:g} mm in the next 2 days',
                       'text': 'Hold irrigation, and postpone spraying and fertilizer top-dressing until it clears so they are not washed off.'})
    if humid_days:
        alerts.append({'level': 'warning', 'title': 'Humid weather: higher risk of fungal disease',
                       'text': f'Check the lower leaves of {crop_txt} for spots or mildew over the next few days. Scan any suspicious leaf.'})
    if hottest >= 38:
        alerts.append({'level': 'danger', 'title': f'Heat: up to {hottest:g}°C this week',
                       'text': 'Irrigate early morning or evening, mulch to keep moisture, and avoid transplanting in the afternoon.'})
    if coldest <= 4:
        alerts.append({'level': 'danger', 'title': f'Frost risk: down to {coldest:g}°C',
                       'text': 'Give a light irrigation in the evening and cover nurseries and young plants overnight.'})
    if windiest >= 25:
        alerts.append({'level': 'warning', 'title': f'Strong wind: up to {windiest:g} km/h',
                       'text': 'Avoid spraying — drift wastes chemical. Stake tall or fruit-laden plants.'})
    if rain_5d < 1 and hottest >= 32:
        alerts.append({'level': 'warning', 'title': 'Dry and warm for the next 5 days',
                       'text': 'Check soil moisture at root depth and plan irrigation, especially for crops at flowering.'})
    if not alerts:
        alerts.append({'level': 'success', 'title': 'Good conditions for field work',
                       'text': 'No rain, heat or strong wind expected in the next 2 days — a good window for spraying, weeding or fertilizer.'})
    return alerts
