import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import altair as alt
from collections import defaultdict

API_KEY = ""
try:
    API_KEY = st.secrets["OPENWEATHER_API_KEY"]
    if not API_KEY:
        st.error("OPENWEATHER_API_KEY не найден в секретах Streamlit. Пожалуйста, добавьте ключ в настройки приложения.")
        st.stop()
except KeyError:
    st.error("OPENWEATHER_API_KEY не найден в секретах Streamlit. Пожалуйста, добавьте ключ в настройки приложения.")
    st.stop()


def get_weather_data(lat, lon):
    url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "units": "metric",
        "lang": "ru",
        "appid": API_KEY
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


st.title("🌦️ Погода")

# Ввод локаций
locations = {}
for i in range(1, 5):
    st.subheader(f"Локация {i}")
    name = st.text_input(f"Название локации {i}:", value=f"Место {i}", key=f"name_{i}")
    lat = st.number_input(f"Широта {i}:", value=55.75, format="%.6f", key=f"lat_{i}")
    lon = st.number_input(f"Долгота {i}:", value=37.61, format="%.6f", key=f"lon_{i}")
    locations[name] = (lat, lon)

# Выбор локаций
st.markdown("---")
selected_locations = st.multiselect("Выберите локации для отображения погоды:", options=list(locations.keys()))

if selected_locations:
    if st.button("Показать погоду для выбранных локаций"):
        with st.spinner("Получаем данные..."):
            for name in selected_locations:
                lat, lon = locations[name]
                st.markdown(f"---")
                st.subheader(f"📍 Погода в {name}")
                try:
                    data = get_weather_data(lat, lon)

                    forecast_list = data["list"]

                    # Текущая погода — первая запись
                    current = forecast_list[0]
                    st.write(f"Температура: {current['main']['temp']} °C")
                    st.write(f"Ветер: {current['wind']['speed']} м/с")
                    st.write(f"Облачность: {current['clouds']['all']} %")
                    pressure_mmHg = round(current['main']['pressure'] * 0.75006)
                    st.write(f"Давление: {pressure_mmHg} мм рт. ст.")
                    rain = current.get('rain', {}).get('3h', 0)
                    snow = current.get('snow', {}).get('3h', 0)
                    st.write(f"Дождь: {rain} мм за 3 ч")
                    st.write(f"Снег: {snow} мм за 3 ч")

                    st.subheader("🔮 Прогноз на 3 дня")

                    # Группировка по дате
                    grouped = defaultdict(list)
                    for entry in forecast_list:
                        date_str = entry["dt_txt"].split(" ")[0]
                        grouped[date_str].append(entry)

                    forecast_days = sorted(grouped.keys())[1:4]

                    temp_records = []
                    wind_records = []
                    cloud_records = []
                    pop_records = []

                    for date in forecast_days:
                        day_data = grouped[date]
                        temps = [x["main"]["temp"] for x in day_data]
                        wind_speeds = [x["wind"]["speed"] for x in day_data]
                        clouds = [x["clouds"]["all"] for x in day_data]
                        pops = [x.get("pop", 0) for x in day_data]

                        temp_day = max(temps)
                        temp_night = min(temps)

                        temp_records.append({"Дата": date, "Температура": temp_day, "Время суток": "День"})
                        temp_records.append({"Дата": date, "Температура": temp_night, "Время суток": "Ночь"})
                        wind_records.append({"Дата": date, "Скорость ветра": sum(wind_speeds) / len(wind_speeds)})
                        cloud_records.append({"Дата": date, "Облачность": sum(clouds) / len(clouds)})
                        pop_records.append({"Дата": date, "Вероятность осадков": int(max(pops) * 100)})

                        st.write(f"📅 {date}")
                        st.write(f"Температура: день {temp_day} °C, ночь {temp_night} °C")
                        st.write(f"Облачность: {int(sum(clouds) / len(clouds))} %")
                        st.write(f"Вероятность осадков: {int(max(pops) * 100)} %")

                    # Графики
                    df_temp = pd.DataFrame(temp_records)
                    df_wind = pd.DataFrame(wind_records)
                    df_cloud = pd.DataFrame(cloud_records)
                    df_pop = pd.DataFrame(pop_records)

                    chart_temp = alt.Chart(df_temp).mark_line(point=True).encode(
                        x='Дата',
                        y='Температура',
                        color='Время суток',
                        tooltip=['Дата', 'Время суток', 'Температура']
                    ).properties(width=600, height=300, title='Динамика температуры на 3 дня')

                    chart_wind = alt.Chart(df_wind).mark_line(point=True, color='green').encode(
                        x='Дата',
                        y='Скорость ветра',
                        tooltip=['Дата', 'Скорость ветра']
                    ).properties(width=600, height=200, title='Скорость ветра (м/с)')

                    chart_cloud = alt.Chart(df_cloud).mark_line(point=True, color='gray').encode(
                        x='Дата',
                        y='Облачность',
                        tooltip=['Дата', 'Облачность']
                    ).properties(width=600, height=200, title='Облачность (%)')

                    chart_pop = alt.Chart(df_pop).mark_line(point=True, color='blue').encode(
                        x='Дата',
                        y='Вероятность осадков',
                        tooltip=['Дата', 'Вероятность осадков']
                    ).properties(width=600, height=200, title='Вероятность осадков (%)')

                    combined_chart = alt.vconcat(
                        chart_temp,
                        chart_wind,
                        chart_cloud,
                        chart_pop,
                        spacing=20
                    )
                    st.altair_chart(combined_chart, use_container_width=True)

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 401:
                        st.error(f"Ошибка аутентификации для {name}: Неверный API-ключ OpenWeatherMap")
                    else:
                        st.error(f"Ошибка HTTP ({e.response.status_code}) для {name}: {e.response.reason}")
                except Exception as e:
                    st.error(f"Ошибка при получении данных для {name}: {str(e)}")
