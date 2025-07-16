import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import altair as alt

API_KEY = st.secrets["OPENWEATHER_API_KEY"]

def get_weather_data(lat, lon):
    url = "https://api.openweathermap.org/data/2.5/onecall"
    params = {
        "lat": lat,
        "lon": lon,
        "units": "metric",
        "lang": "ru",
        "exclude": "minutely,hourly,alerts",
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

# Выбор локаций для отображения
st.markdown("---")
selected_locations = st.multiselect("Выберите локации для отображения погоды:", options=list(locations.keys()))

if st.button("Показать погоду для выбранных локаций") and selected_locations:
    with st.spinner("Получаем данные..."):
        for name in selected_locations:
            lat, lon = locations[name]
            st.markdown(f"---")
            st.subheader(f"📍 Погода в {name}")
            try:
                data = get_weather_data(lat, lon)

        if "current" in data:
            current = data["current"]
            st.write(f"Температура: {current['temp']} °C")
            st.write(f"Ветер: {current['wind_speed']} м/с")
            st.write(f"Облачность: {current['clouds']} %")
            pressure_mmHg = round(current['pressure'] * 0.75006)
            st.write(f"Давление: {pressure_mmHg} мм рт. ст.")
            rain = current.get('rain', {}).get('1h', 0)
            snow = current.get('snow', {}).get('1h', 0)
            st.write(f"Дождь: {rain} мм/ч")
            st.write(f"Снег: {snow} мм/ч")

            st.subheader("🔮 Прогноз на 3 дня")

            forecast_days = data["daily"][1:4]

            # Формируем датафреймы для графиков
            temp_records = []
            wind_records = []
            cloud_records = []
            pop_records = []

            for day in forecast_days:
                date = datetime.fromtimestamp(day['dt']).strftime('%Y-%m-%d')

                temp_records.append({"Дата": date, "Температура": day['temp']['day'], "Время суток": "День"})
                temp_records.append({"Дата": date, "Температура": day['temp']['night'], "Время суток": "Ночь"})

                wind_records.append({"Дата": date, "Скорость ветра": day['wind_speed']})
                cloud_records.append({"Дата": date, "Облачность": day['clouds']})
                pop_records.append({"Дата": date, "Вероятность осадков": int(day['pop'] * 100)})

                st.write(f"📅 {date}")
                st.write(f"Температура: день {day['temp']['day']} °C, ночь {day['temp']['night']} °C")
                st.write(f"Облачность: {day['clouds']} %")
                st.write(f"Вероятность осадков: {int(day['pop'] * 100)} %")
                if "rain" in day:
                    st.write(f"Дождь: {day['rain']} мм")
                if "snow" in day:
                    st.write(f"Снег: {day['snow']} мм")
                st.write("---")

            df_temp = pd.DataFrame(temp_records)
            df_wind = pd.DataFrame(wind_records)
            df_cloud = pd.DataFrame(cloud_records)
            df_pop = pd.DataFrame(pop_records)

            # Графики
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

            st.altair_chart(chart_temp, use_container_width=True)
            st.altair_chart(chart_wind, use_container_width=True)
            st.altair_chart(chart_cloud, use_container_width=True)
            st.altair_chart(chart_pop, use_container_width=True)

            except requests.exceptions.HTTPError as e:
                st.error(f"Ошибка HTTP для {name}: {e}")
            except Exception as e:
                st.error(f"Ошибка при получении данных для {name}: {e}")
        else:
            st.error(f"Ошибка при получении данных для {name}. Проверьте координаты и API-ключ.")
