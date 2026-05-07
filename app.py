import streamlit as st
import pandas as pd
import io
from datetime import date
import plotly.express as px
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from fpdf import FPDF
import numpy as np
import hashlib

# ===========================
# GLOBAL FIGURE STYLING (FOR LATEX EXPORT)
# ===========================
def beautify_fig(fig):
    fig.update_layout(
        template="plotly_dark",
        font=dict(size=18),  # Bigger text for LaTeX
        title=dict(font=dict(size=22)),
        xaxis=dict(title_font=dict(size=18), tickfont=dict(size=16)),
        yaxis=dict(title_font=dict(size=18), tickfont=dict(size=16)),
        legend=dict(font=dict(size=16)),
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig

# ===========================
# PAGE CONFIG
# ===========================
st.set_page_config(page_title="VAYA Shuttle Hybrid Dashboard", layout="wide")

# ===========================
# PASSWORD PROTECTION
# ===========================
PASSWORD_HASH = hashlib.sha256("VayaSecure123!".encode()).hexdigest()
st.sidebar.header("🔒 Login")
password = st.sidebar.text_input("Enter Password", type="password")
if hashlib.sha256(password.encode()).hexdigest() != PASSWORD_HASH:
    st.warning("Incorrect password. Enter the correct password to access the dashboard.")
    st.stop()

# ===========================
# CLEAN DARK STYLING
# ===========================
st.markdown("""
<style>
section[data-testid="stSidebar"] {background-color:#0f172a;}
section[data-testid="stSidebar"] * {color:#f8fafc !important;}
[data-testid="stMetric"] {background-color:transparent; border:none;}
</style>
""", unsafe_allow_html=True)

st.title("🚍 VAYA Shuttle Hybrid Executive Dashboard")
st.caption("Advanced Business KPIs + Statistical Analysis + Operational Intelligence")

# ===========================
# SESSION STATE
# ===========================
if "manual_data" not in st.session_state:
    st.session_state.manual_data = pd.DataFrame()
if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = pd.DataFrame()

vehicle_rates = {"4 seater":1.0,"7 seater":1.2,"15-18 seater":1.57,"bus":2.0}
drivers_list = ["Elton","Dave","Vince","P-gun"]

# ===========================
# SIDEBAR MENU
# ===========================
st.sidebar.title("📊 Dashboard Menu")
menu = st.sidebar.radio(
    "Select Module",
    [
        "DATA ENTRY & UPLOAD",
        "OVERVIEW & KPIs",
        "DESCRIPTIVE STATISTICS",
        "REGRESSION ANALYSIS",
        "RESIDUAL DIAGNOSTICS",
        "TIME SERIES FORECASTING",
        "ROUTE HOTSPOTS",
        "FLEET USAGE",
        "CORPORATE CLIENT ANALYSIS",
        "REPORTS"
    ]
)

# ===========================
# DATA ENTRY & UPLOAD
# ===========================
if menu == "DATA ENTRY & UPLOAD":

    uploaded_file = st.file_uploader("Upload Shuttle Excel File", type=["xlsx"])

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.astype(str).str.strip()

        # ---- FULL EXCEL MAPPING ----
        rename_map = {
            "Date":"date",
            "No. of Buses":"no_of_buses",
            "Trips/bus":"trips_per_bus",
            "Total Trips":"total_trips",
            "Billable Trips":"billable_trips",
            "Number of people":"passengers",
            "Coperate Name":"corporate_name",
            "Vehichle Type":"vehicle_type",
            "Distance":"distance_km",
            "Total fare":"total_fare",
            "ODS Commission":"revenue",
            "Pickup points & Drop Off Locations":"route"
        }

        df = df.rename(columns=rename_map)

        # ---- CLEAN NUMERIC ----
        numeric_cols = [
            "no_of_buses","trips_per_bus","total_trips",
            "billable_trips","passengers",
            "distance_km","total_fare","revenue"
        ]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        # ---- HANDLE CATEGORICAL ----
        for col in ["vehicle_type","route","corporate_name"]:
            if col not in df.columns:
                df[col] = "Unknown"
            df[col] = df[col].fillna("Unknown").astype(str)

        # ---- ADD SOURCE FLAG ----
        df["revenue_source"] = "ODS Commission"

        df = df.dropna(subset=["date"])

        st.session_state.uploaded_data = df
        st.success("✅ Excel uploaded & fully integrated")
        st.dataframe(df, use_container_width=True)

    st.divider()

    # ===========================
    # MANUAL ENTRY
    # ===========================
    with st.form("manual_entry_form"):
        c1,c2,c3 = st.columns(3)

        with c1:
            trip_date = st.date_input("Trip Date", date.today())
            vehicle_type = st.selectbox("Vehicle Type", list(vehicle_rates.keys()))
            driver = st.selectbox("Driver", drivers_list)

        with c2:
            route = st.text_input("Route")
            corporate = st.text_input("Corporate Name")
            passengers = st.number_input("Passengers", min_value=0)

        with c3:
            distance = st.number_input("Distance (km)", min_value=0.0)

        rate = vehicle_rates[vehicle_type]
        total_fare = rate * distance
        revenue = total_fare * 0.17

        submitted = st.form_submit_button("Add Trip")

    if submitted:
        new_row = pd.DataFrame([{
            "date":trip_date,
            "vehicle_type":vehicle_type,
            "route":route if route else "Unknown",
            "driver":driver,
            "passengers":passengers,
            "distance_km":distance,
            "corporate_name":corporate if corporate else "Unknown",
            "rate_per_km":rate,
            "total_fare":total_fare,
            "revenue":revenue,
            "revenue_source":"Manual Calculation"
        }])

        st.session_state.manual_data = pd.concat(
            [st.session_state.manual_data,new_row],
            ignore_index=True
        )

        st.success("✅ Trip added successfully")

# ===========================
# MERGE DATA
# ===========================
def get_combined_data():
    dfs=[]
    if not st.session_state.manual_data.empty:
        dfs.append(st.session_state.manual_data)
    if not st.session_state.uploaded_data.empty:
        dfs.append(st.session_state.uploaded_data)
    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col in ["vehicle_type","route","corporate_name"]:
        if col not in df.columns:
            df[col] = "Unknown"
        df[col] = df[col].fillna("Unknown").astype(str)

    return df.dropna(subset=["date"])

df_all = get_combined_data()

# ===========================
# FILTERS
# ===========================
filtered_df = df_all.copy()

if not df_all.empty:
    st.sidebar.subheader("📌 Filters")

    min_date, max_date = df_all["date"].min(), df_all["date"].max()
    date_range = st.sidebar.date_input("Select Date Range",[min_date,max_date])

    vehicle_filter = st.sidebar.multiselect(
        "Vehicle Type",
        sorted(df_all["vehicle_type"].unique()),
        default=sorted(df_all["vehicle_type"].unique())
    )

    route_filter = st.sidebar.multiselect(
        "Route",
        sorted(df_all["route"].unique()),
        default=sorted(df_all["route"].unique())
    )

    corporate_filter = st.sidebar.multiselect(
        "Corporate",
        sorted(df_all["corporate_name"].unique()),
        default=sorted(df_all["corporate_name"].unique())
    )

    filtered_df = df_all[
        (df_all["date"] >= pd.to_datetime(date_range[0])) &
        (df_all["date"] <= pd.to_datetime(date_range[1])) &
        (df_all["vehicle_type"].isin(vehicle_filter)) &
        (df_all["route"].isin(route_filter)) &
        (df_all["corporate_name"].isin(corporate_filter))
    ]

if menu != "DATA ENTRY & UPLOAD" and filtered_df.empty:
    st.warning("⚠ No data available.")
    st.stop()

# ===========================
# OVERVIEW & KPIs
# ===========================
if menu=="OVERVIEW & KPIs":

    df = filtered_df.copy()
    df["day"]=df["date"].dt.date
    df["month"]=df["date"].dt.to_period("M")

    total_revenue = df["revenue"].sum()
    total_trips = len(df)

    avg_trips_day = df.groupby("day").size().mean()
    avg_trips_month = df.groupby("month").size().mean()
    avg_rev_day = df.groupby("day")["revenue"].sum().mean()
    avg_corp_day = df.groupby("day")["corporate_name"].nunique().mean()

    monthly_rev = df.groupby("month")["revenue"].sum()
    growth_rate = monthly_rev.pct_change().mean()*100

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Revenue", f"${total_revenue:,.2f}")
    c2.metric("Total Trips", total_trips)
    c3.metric("Monthly Growth Rate (%)", f"{growth_rate:.2f}%")
    c4.metric("Avg Corporate Clients / Day", round(avg_corp_day,2))

    c5,c6,c7 = st.columns(3)
    c5.metric("Avg Trips / Day", round(avg_trips_day,2))
    c6.metric("Avg Trips / Month", round(avg_trips_month,2))
    c7.metric("Avg Revenue / Day", f"${avg_rev_day:,.2f}")

    daily_rev = df.groupby("day")["revenue"].sum().reset_index()
    fig = px.line(daily_rev,x="day",y="revenue",template="plotly_dark",markers=True)
    fig = beautify_fig(fig)
    st.plotly_chart(fig, use_container_width=True)


# ===========================
# DESCRIPTIVE STATISTICS
# ===========================
if menu=="DESCRIPTIVE STATISTICS":
    df = filtered_df.copy()
    st.write(df["revenue"].describe())

    fig = px.histogram(df,x="revenue",template="plotly_dark")
    st.plotly_chart(fig,use_container_width=True)

    fig = px.box(df,y="distance_km",template="plotly_dark")
    st.plotly_chart(fig,use_container_width=True)

    corr = df[["revenue","distance_km","passengers"]].corr()
    fig = px.imshow(corr,text_auto=True,template="plotly_dark",color_continuous_scale="Blues")
    fig = beautify_fig(fig)
    st.plotly_chart(fig, use_container_width=True)

# ===========================
# REGRESSION ANALYSIS
# ===========================
if menu == "REGRESSION ANALYSIS":

    df = filtered_df.copy()

    df = df[["distance_km", "passengers", "vehicle_type", "revenue"]].dropna()

    if len(df) < 5:
        st.warning("Not enough data for regression.")
    else:
        df_encoded = pd.get_dummies(df, columns=["vehicle_type"], drop_first=True)

        X = df_encoded.drop(columns=["revenue"])
        y = df_encoded["revenue"]

        model = LinearRegression()
        model.fit(X, y)
        st.write("Intercept (β₀):", model.intercept_)

        y_pred = model.predict(X)

        r2 = r2_score(y, y_pred)

        st.subheader("Model Performance")
        st.metric("R² Score", round(r2, 4))

        coef_df = pd.DataFrame({
            "Variable": X.columns,
            "Coefficient": model.coef_
        })

        st.subheader("Regression Coefficients")
        st.dataframe(coef_df, use_container_width=True)

        fig = px.scatter(
            x=y,
            y=y_pred,
            labels={"x": "Actual Revenue", "y": "Predicted Revenue"},
            template="plotly_dark"
        )
        fig = beautify_fig(fig)
        st.plotly_chart(fig, use_container_width=True)

# ===========================
# RESIDUAL DIAGNOSTICS
# ===========================
if menu == "RESIDUAL DIAGNOSTICS":

    df = filtered_df.copy()
    df = df[["distance_km", "passengers", "vehicle_type", "revenue"]].dropna()

    if len(df) < 5:
        st.warning("Not enough data.")
    else:
        df_encoded = pd.get_dummies(df, columns=["vehicle_type"], drop_first=True)

        X = df_encoded.drop(columns=["revenue"])
        y = df_encoded["revenue"]

        model = LinearRegression()
        model.fit(X, y)

        fitted = model.predict(X)
        residuals = y - fitted

        fig1 = px.histogram(residuals, nbins=20, template="plotly_dark",
                            title="Residual Distribution")
        fig1 = beautify_fig(fig1)
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.scatter(x=fitted, y=residuals,
                          labels={"x": "Fitted Values", "y": "Residuals"},
                          template="plotly_dark")
        fig2 = beautify_fig(fig2)
        st.plotly_chart(fig2, use_container_width=True)


# ===========================
# TIME SERIES FORECASTING
# ===========================
if menu == "TIME SERIES FORECASTING":

    df = filtered_df.copy()

    daily = df.groupby(df["date"].dt.date)["revenue"].sum().reset_index()
    daily.columns = ["date", "revenue"]

    if len(daily) < 5:
        st.warning("Not enough time data.")
    else:
        daily["t"] = range(len(daily))

        model = LinearRegression()
        model.fit(daily[["t"]], daily["revenue"])

        daily["forecast"] = model.predict(daily[["t"]])

        fig = px.line(daily, x="date", y=["revenue", "forecast"],
                      template="plotly_dark")
        fig = beautify_fig(fig)
        st.plotly_chart(fig, use_container_width=True)


# ===========================
# ROUTE HOTSPOTS
# ===========================
if menu == "ROUTE HOTSPOTS":

    df = filtered_df.copy()

    hotspots = df.groupby("route").agg(
        trips=("route", "count"),
        revenue=("revenue", "sum")
    ).reset_index().sort_values("trips", ascending=False)

    fig = px.bar(hotspots, x="route", y="trips",
                 color="revenue", template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(hotspots, use_container_width=True)



# ===========================
# FLEET USAGE
# ===========================
if menu == "FLEET USAGE":

    df = filtered_df.copy()

    fleet = df.groupby("vehicle_type").agg(
        trips=("vehicle_type", "count"),
        revenue=("revenue", "sum")
    ).reset_index()

    fig = px.pie(fleet, values="trips", names="vehicle_type",
                 template="plotly_dark")
    fig = beautify_fig(fig)
    st.plotly_chart(fig, use_container_width=True)


    st.dataframe(fleet, use_container_width=True)


# ===========================
# CORPORATE CLIENT ANALYSIS
# ===========================
if menu == "CORPORATE CLIENT ANALYSIS":

    df = filtered_df.copy()

    corp = df.groupby("corporate_name").agg(
        trips=("corporate_name", "count"),
        revenue=("revenue", "sum")
    ).reset_index().sort_values("revenue", ascending=False)

    fig = px.bar(corp, x="corporate_name", y="revenue",
                 template="plotly_dark")
    fig = beautify_fig(fig)
    st.plotly_chart(fig, use_container_width=True)
   

    st.dataframe(corp, use_container_width=True)

# ===========================
# REPORTS
# ===========================
if menu == "REPORTS":

    df = filtered_df.copy()

    st.dataframe(df, use_container_width=True)

    # Excel download
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)

    st.download_button(
        "Download Excel Report",
        excel_buffer,
        "shuttle_report.xlsx"
    )

    # PDF download
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "VAYA Shuttle Executive Report", ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"Total Trips: {len(df)}", ln=True)
    pdf.cell(0, 8, f"Total Revenue: ${df['revenue'].sum():,.2f}", ln=True)

    pdf_bytes = pdf.output(dest="S").encode("latin1")

    st.download_button(
        "Download PDF Report",
        pdf_bytes,
        "shuttle_report.pdf"
    )
