import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import altair as alt
from collections import defaultdict

# --- Ключ API ---
API_KEY = ""
try:
    # Предпочтительный способ получения ключа из секретов Streamlit
    API_KEY = st.secrets["OPENWEATHER_API_KEY"]
    if not API_KEY:
        st.error("Ключ OPENWEATHER_API_KEY не найден в секретах Streamlit. Пожалуйста, добавьте его в настройки вашего приложения.")
        st.stop()
except (KeyError, FileNotFoundError):
    # Локальная разработка может не иметь st.secrets, добавьте запасной вариант, если нужно
    st.error("Ключ OPENWEATHER_API_KEY не найден в секретах Streamlit. Пожалуйста, добавьте его в настройки вашего приложения.")
    st.stop()


# --- Функции ---

def get_weather_data(lat, lon):
    """Получает данные о погоде с API OpenWeatherMap."""
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

def map_time_to_period(hour):
    """Сопоставляет час с названием времени суток."""
    if 5 <= hour < 12:
        return "Утро"
    elif 12 <= hour < 18:
        return "День"
    elif 18 <= hour < 23:
        return "Вечер"
    else:
        return "Ночь"

def degrees_to_cardinal(d):
    """Конвертирует градусы в направление ветра."""
    dirs = ["С", "ССВ", "СВ", "ВСВ", "В", "ВЮВ", "ЮВ", "ЮЮВ", "Ю", "ЮЮЗ", "ЮЗ", "ЗЮЗ", "З", "ЗСЗ", "СЗ", "ССЗ"]
    ix = int(round(d / (360. / len(dirs))))
    return dirs[ix % len(dirs)]

# --- Интерфейс приложения ---

st.title("🌦️ Погода")

# Сайдбар для ввода параметров
with st.sidebar:
    st.header("Параметры локаций")
    
    # Пример локаций по умолчанию
    default_locs = {
        "Омск": (54.986689, 73.373765)
    }
    
    # ВАЖНО: Мы должны сначала определить возможные опции для multiselect.
    # Мы будем использовать ключи из default_locs, но виджеты для их редактирования будут ниже.
    location_names_options = list(default_locs.keys())
    
    selected_locations = st.multiselect(
        "Выберите локации для отображения погоды:",
        options=location_names_options,
        default=location_names_options # Выбрать все по умолчанию
    )
    
    utc_offset = st.number_input("Смещение от UTC (часы)", min_value=-12, max_value=14, value=6, step=1)
    
    st.markdown("---")

    # Теперь отображаем поля для ввода данных для каждой локации
    locations = {}
    for i, default_name in enumerate(default_locs.keys(), 1):
        st.subheader(f"Локация {i}")
        default_lat, default_lon = default_locs[default_name]
        
        name = st.text_input(f"Название локации {i}:", value=default_name, key=f"name_{i}")
        lat = st.number_input(f"Широта {i}:", value=default_lat, format="%.6f", key=f"lat_{i}")
        lon = st.number_input(f"Долгота {i}:", value=default_lon, format="%.6f", key=f"lon_{i}")
        locations[name] = (lat, lon)
    
    st.sidebar.markdown("""
    <div style="margin-top: 50px; text-align: center;">
        ©D.Prozorovskiy
    </div>
    """, unsafe_allow_html=True)

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
                    
                    # Преобразуем время UTC в локальное время, добавляя смещение
                    for entry in forecast_list:
                        dt_utc = datetime.strptime(entry["dt_txt"], "%Y-%m-%d %H:%M:%S")
                        local_time = dt_utc + timedelta(hours=utc_offset)
                        entry['local_time'] = local_time
                    
                    # Блок с текущей погодой
                    st.subheader("☀️ Текущая погода (данные: OpenWeatherMap)")                   
                    current = forecast_list[0]
                    weather_description = current['weather'][0]['description'].capitalize()
                    weather_icon = current['weather'][0]['icon']
                    icon_url = f"http://openweathermap.org/img/wn/{weather_icon}@2x.png"

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Температура", f"{current['main']['temp']} °C")
                        st.metric("Ветер", f"{degrees_to_cardinal(current['wind']['deg'])}; {current['wind']['speed']} м/с")

                    with col2:
                        st.metric("Давление", f"{round(current['main']['pressure'] * 0.75006)} мм рт. ст.")
                        st.metric("Облачность", f"{current['clouds']['all']} %")

                    # Блок явлений - под метриками
                    st.markdown(
                        f"<div style='display: flex; align-items: center; margin-top: 20px;'>"
                        f"<img src='{icon_url}' alt='Weather icon' style='width: 50px; margin-right: 10px;'>"
                        f"<span style='font-size: 24px; font-weight: bold;'>{weather_description}</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    st.divider()  # Добавляет тонкую горизонтальную линию
                    
                    
                    # Таблица на 2 дня (10 записей)
                    st.subheader("🗓️ Детальный прогноз на 2 дня")
                    
                    table_data = []
                    for entry in forecast_list[:10]:
                        local_time = entry['local_time']
                        
                        rain = entry.get('rain', {}).get('3h', 0)
                        snow = entry.get('snow', {}).get('3h', 0)
                        precipitation = rain + snow
    
                        table_data.append({
                            "Дата": local_time.strftime("%d.%m"),
                            "Время": f"{local_time.strftime('%H:%M')}, {map_time_to_period(local_time.hour)}",
                            "Явления": entry["weather"][0]["description"].capitalize(),
                            "Темп., °C": round(entry["main"]["temp"]),
                            "Давл.": round(entry['main']['pressure'] * 0.75006),
                            "Ветер, м/с": f"{degrees_to_cardinal(entry['wind']['deg'])};    {round(entry['wind']['speed'])}м/c",
                            "Влажн., %": entry["main"]["humidity"],
                            "Осадки": f"{precipitation:.1f} мм"
                        })
                    
                    df_forecast = pd.DataFrame(table_data)
                    
                    table_height = (10 + 1) * 35 + 3 # Добавляем пиксели для запаса
                    st.dataframe(
                        df_forecast, 
                        use_container_width=True, 
                        hide_index=True, 
                        height=table_height
                    )

                    # --- ГРАФИКИ ---
                    st.subheader("📊 Графики прогноза")
                    grouped = defaultdict(list)
                    for entry in forecast_list:
                        date_str = entry['local_time'].strftime("%Y-%m-%d")
                        grouped[date_str].append(entry)

                    forecast_days = sorted(grouped.keys())

                    temp_records, wind_records, pop_records = [], [], []

                    for date in forecast_days:
                        day_data = grouped[date]
                        if not day_data: continue
                        temps = [x["main"]["temp"] for x in day_data]
                        wind_speeds = [x["wind"]["speed"] for x in day_data]
                        pops = [x.get("pop", 0) for x in day_data]

                        temp_records.append({"Дата": date, "Температура": max(temps), "Время суток": "День"})
                        temp_records.append({"Дата": date, "Температура": min(temps), "Время суток": "Ночь"})
                        wind_records.append({"Дата": date, "Скорость ветра": sum(wind_speeds) / len(wind_speeds)})
                        pop_records.append({"Дата": date, "Вероятность осадков": int(max(pops) * 100)})

                    df_temp = pd.DataFrame(temp_records)
                    df_wind = pd.DataFrame(wind_records)
                    df_pop = pd.DataFrame(pop_records)

                    # Устанавливаем высоту для каждого графика, чтобы сделать их компактнее
                    chart_height = 150

                    chart_temp = alt.Chart(df_temp).mark_line(point=True).encode(
                        x=alt.X('Дата', title=None), # Убираем заголовок оси X, т.к. он будет общим
                        y=alt.Y('Температура', title='Температура, °C'),
                        color='Время суток',
                        tooltip=['Дата', 'Время суток', 'Температура']
                    ).properties(
                        title='Динамика температуры',
                        height=chart_height  # Устанавливаем высоту
                    )

                    chart_wind = alt.Chart(df_wind).mark_line(point=True, color='green').encode(
                        x=alt.X('Дата', title=None), # Убираем заголовок оси X
                        y=alt.Y('Скорость ветра', title='Ветер, м/с'),
                        tooltip=['Дата', 'Скорость ветра']
                    ).properties(
                        title='Средняя скорость ветра',
                        height=chart_height # Устанавливаем высоту
                    )

                    chart_pop = alt.Chart(df_pop).mark_bar(size=15, opacity=0.7, color='blue').encode(
                        x=alt.X('Дата', title='Дата'), # Оставляем заголовок на нижнем графике
                        y=alt.Y('Вероятность осадков', title='Осадки, %'),
                        tooltip=['Дата', 'Вероятность осадков']
                    ).properties(
                        title='Вероятность осадков',
                        height=chart_height # Устанавливаем высоту
                    )

                    # Соединяем графики
                    combined_chart = alt.vconcat(
                        chart_temp,
                        chart_wind,
                        chart_pop
                    ).resolve_scale(
                        x='shared' # Делаем ось X общей для всех
                    )

                    st.altair_chart(combined_chart, use_container_width=True)

                    # --- БЛОК С КНОПКОЙ-ССЫЛКОЙ НА ЯНДЕКС (НА НОВОМ МЕСТЕ) ---
                    yandex_url = f"https://yandex.ru/pogoda/ru?lat={lat}&lon={lon}"
                    st.link_button(f"Подробный прогноз для '{name}' на Яндекс.Погоде ↗", yandex_url)
                    # --- КОНЕЦ БЛОКА ---

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 401:
                        st.error(f"Ошибка аутентификации для {name}: Неверный API-ключ OpenWeatherMap.")
                    else:
                        st.error(f"Ошибка HTTP ({e.response.status_code}) для {name}: {e.response.text}")
                except Exception as e:
                    st.error(f"Произошла ошибка при получении данных для {name}: {str(e)}")
