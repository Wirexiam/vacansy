import streamlit as st
import pandas as pd

st.set_page_config(page_title="Аналитика звонков", layout="wide")

# --- Загрузка витрины
@st.cache_data
def load_data():
    return pd.read_csv("vitrina.csv", delimiter=",", encoding="cp1251")

df = load_data()

# --- Преобразование длительности
df["duratoin_sec"] = df["duratoin_sec"].astype(str).str.replace(",", ".").astype(float)

# --- 🎛 ФИЛЬТРЫ (sidebar)
st.sidebar.header("📌 Фильтры")

# Статусы звонков
all_statuses = df["call_status"].dropna().unique().tolist()
selected_statuses = st.sidebar.multiselect(
    "Статус звонка", options=all_statuses, default=all_statuses
)

# Операторы
all_agents = df["agent_login"].dropna().unique().tolist()
selected_agent = st.sidebar.selectbox("Оператор", ["Все"] + sorted(all_agents))

# Слайдер по длительности
min_dur = int(df["duratoin_sec"].min())
max_dur = int(df["duratoin_sec"].max())
dur_range = st.sidebar.slider(
    "Длительность звонка (сек)", min_value=min_dur, max_value=max_dur,
    value=(min_dur, max_dur)
)

# Кнопка сброса (реально работает как хинт — перезапускает фильтры)
if st.sidebar.button("🔄 Сбросить фильтры"):
    st.experimental_rerun()

# --- Применение фильтров
filtered_df = df[
    df["call_status"].isin(selected_statuses) &
    df["duratoin_sec"].between(dur_range[0], dur_range[1])
]
if selected_agent != "Все":
    filtered_df = filtered_df[filtered_df["agent_login"] == selected_agent]

st.title("📊 Дашборд: Аналитика звонков")
st.subheader("📌 Общая статистика по выбранным параметрам")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📞 Всего звонков", len(filtered_df))

with col2:
    success = filtered_df[filtered_df["call_status"] == "Дозвон, Успешно"]
    st.metric("✅ Успешных", len(success))

with col3:
    conv_subset = filtered_df[filtered_df["call_status"].isin(["Дозвон, Успешно", "Дозвон, Отказ"])]
    success = conv_subset[conv_subset["call_status"] == "Дозвон, Успешно"]
    refused = conv_subset[conv_subset["call_status"] == "Дозвон, Отказ"]

    total = len(success) + len(refused)
    conv = round(len(success) / total * 100, 2) if total > 0 else 0.0

    st.metric("Конверсия", f"{conv} %")


st.subheader("📊 Распределение звонков по статусам")
st.bar_chart(filtered_df["call_status"].value_counts())

st.subheader("⏱ Средняя длительность по статусу")
st.dataframe(
    filtered_df.groupby("call_status")["duratoin_sec"]
    .mean()
    .round(2)
    .sort_values(ascending=False)
    .reset_index()
    .rename(columns={"duratoin_sec": "Средняя длительность (сек)"})
)

st.subheader("📎 Выгрузка данных")
csv = filtered_df.to_csv(index=False, sep=";").encode("cp1251")

st.download_button(
    label="💾 Скачать как CSV",
    data=csv,
    file_name="filtered_calls.csv",
    mime="text/csv"
)

st.subheader("📆 Активность по дате и времени")

# Убедимся, что task_created — это datetime
filtered_df["task_created"] = pd.to_datetime(filtered_df["task_created"], errors="coerce")

# Кол-во звонков по дням
calls_by_day = filtered_df["task_created"].dt.date.value_counts().sort_index()
st.line_chart(calls_by_day)

# Кол-во звонков по часам
calls_by_hour = filtered_df["task_created"].dt.hour.value_counts().sort_index()
st.bar_chart(calls_by_hour)

st.subheader("👥 Конверсия по операторам")

# Только успешные и отказные звонки
conv_df = filtered_df[filtered_df["call_status"].isin(["Дозвон, Успешно", "Дозвон, Отказ"])]

# Группировка по операторам
group_stats = conv_df.groupby(["agent_login", "call_status"]).size().unstack(fill_value=0)
group_stats = group_stats.reindex(columns=["Дозвон, Успешно", "Дозвон, Отказ"], fill_value=0)
group_stats["conversion_%"] = (
    group_stats["Дозвон, Успешно"] /
    (group_stats["Дозвон, Успешно"] + group_stats["Дозвон, Отказ"]).replace(0, 1) * 100
).round(2)

st.dataframe(group_stats.sort_values(by="conversion_%", ascending=False))
