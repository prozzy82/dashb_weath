import streamlit as st
import requests
from datetime import datetime
import pandas as pd
from collections import defaultdict
import altair as alt

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

# Перенос ввода локаций в боковую панель
st.sidebar.title("Ввод локаций")
locations = {}
for i in range(1, 5):
    st.sidebar.subheader(f"Локация {i}")
    name = st.sidebar.text_input(f"Название локации {i}:", value=f"Место {i}", key=f"name_{i}")
    lat = st.sidebar.number_input(f"Широта {i}:", value=55.75, format="%.6f", key=f"lat_{i}")
    lon = st.sidebar.number_input(f"Долгота {i}:", value=37.61, format="%.6f", key=f"lon_{i}")
    locations[name] = (lat, lon)

# Выбор локаций
st.markdown("---")
selected_locations = st.multiselect("Выберите локации для отображения погоды:", options=list(locations.keys()))

if selected_locations:
    if st.button("Показать погоду для выбранных локаций"):
        with st.spinner("Получаем данные..."):
            all_data = []
            error_messages = []
            
            for name in selected_locations:
                lat, lon = locations[name]
                try:
                    data = get_weather_data(lat, lon)
                    forecast_list = data["list"]
                    current = forecast_list[0]
                    
                    # Текущая погода
                    current_data = {
                        "Локация": name,
                        "Температура": current['main']['temp'],
                        "Ветер": current['wind']['speed'],
                        "Давление": round(current['main']['pressure'] * 0.75006),
                        "Облачность": current['clouds']['all'],
                        "Дождь": current.get('rain', {}).get('3h', 0),
                        "Снег": current.get('snow', {}).get('3h', 0)
                    }
                    
                    # Прогноз на 3 дня
                    grouped = defaultdict(list)
                    for entry in forecast_list:
                        date_str = entry["dt_txt"].split(" ")[0]
                        grouped[date_str].append(entry)
                        
                    dates = sorted(grouped.keys())
                    forecast_days = dates[1:4] if len(dates) >= 4 else dates[1:]
                    
                    for i, day in enumerate(forecast_days):
                        day_data = grouped[day]
                        temps = [x["main"]["temp"] for x in day_data]
                        clouds = [x["clouds"]["all"] for x in day_data]
                        pops = [x.get("pop", 0) for x in day_data]
                        
                        current_data[f"День {i+1} Макс"] = max(temps)
                        current_data[f"День {i+1} Мин"] = min(temps)
                        current_data[f"День {i+1} Облачность"] = int(sum(clouds)/len(clouds))
                        current_data[f"День {i+1} Осадки"] = int(max(pops)*100)
                    
                    all_data.append(current_data)
                    
                except Exception as e:
                    error_messages.append(f"Ошибка в {name}: {str(e)}")
            
            # Вывод ошибок
            for error in error_messages:
                st.error(error)
                
            # Формируем и выводим таблицу
            if all_data:
                df = pd.DataFrame(all_data)
                st.table(df.set_index("Локация"))
                
                # Подготовка данных для графиков
                forecast_data = []
                for idx, row in df.iterrows():
                    for day in [1, 2, 3]:
                        if f"День {day} Макс" in row:
                            forecast_data.append({
                                "Локация": idx,
                                "День": f"День {day}",
                                "Показатель": "Макс.температура",
                                "Значение": row[f"День {day} Макс"]
                            })
                            forecast_data.append({
                                "Локация": idx,
                                "День": f"День {day}",
                                "Показатель": "Мин.температура",
                                "Значение": row[f"День {day} Мин"]
                            })
                        if f"День {day} Облачность" in row:
                            forecast_data.append({
                                "Локация": idx,
                                "День": f"День {day}",
                                "Показатель": "Облачность",
                                "Значение": row[f"День {day} Облачность"]
                            })
                        if f"День {day} Осадки" in row:
                            forecast_data.append({
                                "Локация": idx,
                                "День": f"День {day}",
                                "Показатель": "Вероятность осадков",
                                "Значение": row[f"День {day} Осадки"]
                            })
                
                if forecast_data:
                    df_forecast = pd.DataFrame(forecast_data)
                    
                    # Графики для каждой метрики
                    metrics = ["температура", "Облачность", "Вероятность осадков"]
                    for metric in metrics:
                        metric_data = df_forecast[df_forecast['Показатель'].str.contains(metric)]
                        if not metric_data.empty:
                            chart = alt.Chart(metric_data).mark_bar().encode(
                                x=alt.X('День:N', title='День прогноза'),
                                y=alt.Y('sum(Значение):Q', title='Значение'),
                                color='Локация:N',
                                column='Показатель:N'
                            ).properties(
                                width=200,
                                height=300,
                                title=f"{metric.capital()} по локациям"
                            )
                            st.altair_chart(chart)
