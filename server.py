import streamlit as st
from streamlit_js_eval import streamlit_js_eval

import os
import pandas as pd
from PIL import Image, UnidentifiedImageError

import altair as alt

st.set_page_config(
    page_title="Traffic Dashboard KIK",
    #page_icon="",
    layout="wide",
    #initial_sidebar_state="expanded"
    )

pilihan_chart = st.sidebar.selectbox(
    "Pilih chart yang ingin disimpan:",
    ("Heatmap Kecepatan Kendaraan", "Jumlah Kendaraan Harian (1 minggu)", "Jumlah Kendaraan per Jam"
     , "Jumlah Kendaraan Menurut Kategori", "Kecepatan Kendaraan per Jam")
)

with st.sidebar:
    mode = st.radio(
        "Pilih mode dashboard",
        ("Arah Masuk Kawasan", "Arah Keluar Kawasan")
    )

#alt.themes.enable("dark")

@st.cache_resource
def weekly_chart(df): 
    #Beberapa kendaraan ada yang terdeteksi sebagai dua atau lebih jenis kendaraan
    #Diubah menjadi satu jenis kendaraan, berdasarkan hasil modus jenis_kendaraan
    df['jenis_kendaraan'] = df['nomor_identifikasi'].map(df.groupby('nomor_identifikasi')['jenis_kendaraan']
                                                         .agg(lambda x: x.mode()[0]))
    
    df['tanggal'] = pd.to_datetime(df['waktu_terekam']).dt.date
    
    uniques = df.groupby(['tanggal', 'nomor_identifikasi']).nunique()
    
    #buang nomor_identifikasi yang terekam di kurang dari 3 frame
    uniques = uniques[uniques['waktu_terekam'].ge(3)]
    
    filtered_df = df[df['nomor_identifikasi'].isin(uniques.index.get_level_values('nomor_identifikasi'))]
    filtered_df = filtered_df.groupby('tanggal')['nomor_identifikasi'].nunique().reset_index(name = "jumlah_kendaraan")
    filtered_df['tanggal'] = filtered_df['tanggal'].astype(str)
    
    domain_range = 0
    
    if len(filtered_df) != 0:
        domain_range = int(filtered_df['jumlah_kendaraan'].max() * 1.25)
    
    #ada bug, saat dikasih domain datetime selain dari library Altair di X, malah ilang tanggalnya
    a  = (alt.Chart(filtered_df).mark_bar().encode(
            alt.X('tanggal:O').title('Tanggal'),
            alt.Y('jumlah_kendaraan').title('Jumlah Kendaraan').scale(domain = (0, domain_range)), #max y-axis = jumlah maksimum kendaraan * 1.25
        ))
    
    text = a.mark_text(
        align='center',
        baseline='middle',
        dy=-10, 
        fontSize=15,
        color='black'
        ).encode(
            text='jumlah_kendaraan:Q',
            tooltip=alt.value(None)
        )
    
    chart = a + text
    chart = chart.configure_axis(
            labelFontSize=15,
            titleFontSize=15
            ).properties(
            height=320,
            width=screen_width/2.5,
            ).interactive()
    
    return chart 

def isRecordExist(record_path):
    return os.path.isfile(record_path)
    
def weekly_component():
    st.markdown('#### Jumlah Kendaraan Harian (1 minggu)')
       
    col = st.columns((1,1))
    container = st.container(height = 320, border = False)
    
    with col[0]:
        d_start = st.date_input("Dari tanggal:", key = 'weekly_component_start_date', format="DD/MM/YYYY")
    
    with col[1]:
        d_end = st.date_input("Sampai tanggal (periode maksimal 7 hari):", key = 'weekly_component_end_date', format="DD/MM/YYYY")
    
    with container:
        if (d_end - d_start).days >= 7 :
            st.markdown(''':red[Periode yang dapat ditampilkan maksimal tujuh hari!]''')
        elif (d_end - d_start).days < 0:
            st.markdown(''':red[Tanggal awal harus lebih kecil dari tanggal akhir!]''')
        else:
            df = concatCSVtoDataframe(d_start, d_end)
            chart = weekly_chart(df)
            st.altair_chart(chart, theme = None)

@st.cache_resource
def vehicle_count_per_day_chart(df):
    #Beberapa kendaraan ada yang terdeteksi sebagai dua atau lebih jenis kendaraan
    #Diubah menjadi satu jenis kendaraan, berdasarkan hasil modus jenis_kendaraan
    df['jenis_kendaraan'] = df['nomor_identifikasi'].map(df.groupby('nomor_identifikasi')['jenis_kendaraan']
                                                         .agg(lambda x: x.mode()[0]))

    df = smallVehicletoCar(df)
    
    uniques = df.groupby(['nomor_identifikasi']).nunique()
    
    #buang nomor_identifikasi yang terekam di kurang dari 3 frame
    uniques = uniques[uniques['waktu_terekam'].ge(3)]
    
    filtered_df = df[df['nomor_identifikasi'].isin(uniques.index.get_level_values('nomor_identifikasi'))]
    filtered_df['1_hour_interval'] = filtered_df['waktu_terekam'].dt.floor('1h')
    
    filtered_df_all = filtered_df.groupby('1_hour_interval').nunique().reset_index()
    filtered_df_by_category = filtered_df.groupby(['1_hour_interval', 'jenis_kendaraan']).nunique().reset_index()

    domain_range = 0
    
    if len(filtered_df_all) != 0:
        domain_range = int(filtered_df_all['nomor_identifikasi'].max() * 1.25)
    
    opacity = alt.value(1)
    
    if len(filtered_df_all) > 16:
        opacity = alt.value(0)
    
    a_all  = alt.Chart(filtered_df_all).mark_bar(point = {"filled": False, "fill": "white"}).encode(
            alt.X('1_hour_interval', axis = alt.Axis(format = "%H:%M", labelAngle = 0, tickCount=4)).title('Rentang Waktu'),
            alt.Y('nomor_identifikasi').title('Jumlah Kendaraan').scale(domain = (0, domain_range)),
            strokeWidth=alt.value(4)
            )
    
    text_all = a_all.mark_text(
        align='center',
        baseline='middle',
        dy=-15, 
        fontSize=15,
        color='black'
        ).encode(
            opacity=opacity,
            text='nomor_identifikasi:Q',
            tooltip=alt.value(None)
        )
    
    chart_all = a_all + text_all
    chart_all = chart_all.configure_axis(
            labelFontSize=15,
            titleFontSize=15
            ).properties(
                width = screen_width/2.5,
                height = 320
            )
            
    domain_range_by_category = 0
    
    if len(filtered_df_by_category) != 0:
        domain_range_by_category = int(filtered_df_by_category['nomor_identifikasi'].max() * 1.25)
            
    a_by_category = alt.Chart(filtered_df_by_category).mark_line(point = {"filled": False, "fill": "white"}).encode(
        alt.X('1_hour_interval', axis = alt.Axis(format = "%H:%M", labelAngle = 0, tickCount = 4)).title('Rentang Waktu'),
        alt.Y('nomor_identifikasi:Q').title('Jumlah Kendaraan').scale(domain = (0, domain_range_by_category)),
        alt.Color('jenis_kendaraan:N').title('Jenis Kendaraan'),
        strokeWidth=alt.value(4)
    )
            
    chart_by_category = a_by_category.configure_axis(
            labelFontSize=15,
            titleFontSize=15
            ).properties(
                width = screen_width/2.5,
                height = 320
            )

    return chart_all, chart_by_category


#Van dan pickup akan di-label sebagai mobil
def smallVehicletoCar(df):
    df.loc[df['jenis_kendaraan'] == 'van', 'jenis_kendaraan'] = 'mobil'
    df.loc[df['jenis_kendaraan'] == 'pickup', 'jenis_kendaraan'] = 'mobil'
    return df

@st.cache_resource
def vehicle_count_per_day_by_category_chart(df):
    #Beberapa kendaraan ada yang terdeteksi sebagai dua atau lebih jenis kendaraan
    #Diubah menjadi satu jenis kendaraan, berdasarkan hasil modus jenis_kendaraan
    df['jenis_kendaraan'] = df['nomor_identifikasi'].map(df.groupby('nomor_identifikasi')['jenis_kendaraan']
                                                         .agg(lambda x: x.mode()[0]))
    
    df = smallVehicletoCar(df)
    
    uniques = df.groupby(['nomor_identifikasi']).nunique()
    
    #buang nomor_identifikasi yang terekam di kurang dari 3 frame
    uniques = uniques[uniques['waktu_terekam'].ge(3)]
    
    filtered_df = df[df['nomor_identifikasi'].isin(uniques.index.get_level_values('nomor_identifikasi'))]
    vehicle_count_df = filtered_df[['nomor_identifikasi', 'jenis_kendaraan']].value_counts().reset_index()
    vehicle_count_df = vehicle_count_df['jenis_kendaraan'].value_counts().reset_index()
    
    domain_range = 0
    if len(vehicle_count_df) != 0:
        domain_range = int(vehicle_count_df['count'].max() * 1.25)
    
    a  = alt.Chart(vehicle_count_df).mark_bar().encode(
            alt.X('jenis_kendaraan', axis = alt.Axis(labelAngle = 0)).title('Jenis Kendaraan'),
            alt.Y('count').title('Jumlah Kendaraan').scale(domain = (0, domain_range)),
    )
    
    text = a.mark_text(
        align='center',
        baseline='middle',
        dy=-10, 
        fontSize=15,
        color='black'
        ).encode(
            text='count:Q',
            tooltip=alt.value(None)
        )
    
    chart = a + text
    chart = chart.configure_axis(
            labelFontSize=15,
            titleFontSize=15
            ).properties(
                width = screen_width/2.5,
                height = 320
            )
    
    return chart

@st.cache_resource
def vehicle_speed_per_day_chart(df):
    df['kecepatan'] = df['kecepatan'].abs()
    
    #Beberapa kendaraan ada yang terdeteksi sebagai dua atau lebih jenis kendaraan
    #Diubah menjadi satu jenis kendaraan, berdasarkan hasil modus jenis_kendaraan
    df['jenis_kendaraan'] = df['nomor_identifikasi'].map(df.groupby('nomor_identifikasi')['jenis_kendaraan']
                                                         .agg(lambda x: x.mode()[0]))
    df = smallVehicletoCar(df)
    
    uniques = df.groupby(['nomor_identifikasi']).nunique()
    
    #buang nomor_identifikasi yang terekam di kurang dari 3 frame
    uniques = uniques[uniques['waktu_terekam'].ge(3)]
    
    df = df[df['nomor_identifikasi'].isin(uniques.index.get_level_values('nomor_identifikasi'))]
    
    df['interval'] = df['waktu_terekam'].dt.floor('30min')
    df_mean_all = df[['interval', 'kecepatan']].groupby(by=['interval']).mean().round(2).reset_index()
    df_mean_by_category = df[['interval', 'kecepatan', 'jenis_kendaraan']].groupby(by=['interval', 'jenis_kendaraan']).mean().round(2).reset_index()
    
    domain_range_all = 0
    
    if len(df_mean_all) != 0:
        domain_range_all = (int(df_mean_all['kecepatan'].max()/10) + bool(df_mean_all['kecepatan'].max()%1))*10
    
    opacity = alt.value(1)
    
    if len(df_mean_all) > 16:
        opacity = alt.value(0)
    
    a_all  = alt.Chart(df_mean_all).mark_line(point = {"filled": False, "fill": "blue"}).encode(
        alt.X('interval', axis = alt.Axis(format = "%H:%M", labelAngle = 0, tickCount = len(df_mean_all))).title('Rentang Waktu'),
        alt.Y('kecepatan').title('Rerata Kecepatan (km/jam)').scale(domain = (0, int(domain_range_all * 1.25))),
        strokeWidth=alt.value(4)
        )
    
    text_all = a_all.mark_text(
        align='center',
        baseline='middle',
        dy=-15, 
        fontSize=15,
        color='black'
        ).encode(
            text='kecepatan:Q',
            opacity = opacity,
            tooltip=alt.value(None)
        )
    
    chart_total = a_all + text_all
    chart_total = chart_total.configure_axis(
            labelFontSize=15,
            titleFontSize=15
            ).properties(
                width = screen_width/2.5,
                height = 320
            )
            
    domain_range_by_category = 0
    
    if len(df_mean_by_category) != 0:
        domain_range_by_category = int(df_mean_by_category['kecepatan'].max() * 1.25)
    
    a_by_category = alt.Chart(df_mean_by_category).mark_line(point = {"filled": False, "fill": "white"}).encode(
        alt.X('interval', axis = alt.Axis(format = "%H:%M", labelAngle = 0, tickCount = 4)).title('Rentang Waktu'),
        alt.Y('kecepatan:Q').title('Rerata Kecepatan (km/jam)').scale(domain = (0, domain_range_by_category)),
        alt.Color('jenis_kendaraan:N').title('Jenis Kendaraan'),
        strokeWidth=alt.value(4)
        )
            
    chart_by_category = a_by_category.configure_axis(
            labelFontSize=15,
            titleFontSize=15
            ).properties(
                width = screen_width/2.5,
                height = 320
            )

    return chart_total, chart_by_category
    
    
def vehicle_count_per_day_component():
    st.markdown('#### Jumlah Kendaraan per Jam')
    d = st.date_input("Pilih tanggal untuk ditampilkan:", key = 'vehicle_count_per_day_date', format="DD/MM/YYYY")
    col = st.columns((1,1))
    
    with col[0]:
        waktu_awal = st.time_input("Dari jam:", value=None, key = 'vehicle_count_per_day_time_start', step = 3600)
    
    with col[1]:
        waktu_akhir = st.time_input("Sampai jam", value=None, key = 'vehicle_count_per_day_time_end', step = 3600)
    
    df = concatCSVtoDataframe(d, d)
    df = selectbyTimeframe(df, waktu_awal, waktu_akhir)
    chart_all, chart_by_category = vehicle_count_per_day_chart(df)
    tab1, tab2 = st.tabs(["Jumlah Keseluruhan", "Jumlah per Kategori"])
    
    with tab1:
        st.altair_chart(chart_all, theme = None)
    
    with tab2:
        st.altair_chart(chart_by_category, theme = None)

def vehicle_count_per_day_by_category_component():
    st.markdown('#### Jumlah Kendaraan Menurut Kategori')
    d = st.date_input("Pilih tanggal untuk ditampilkan:", key = 'vehicle_count_per_day_by_category_date', format="DD/MM/YYYY")
    
    df = concatCSVtoDataframe(d, d)
    chart = vehicle_count_per_day_by_category_chart(df)

    container = st.container(height=320, border=False)
    
    with container:
        st.altair_chart(chart, theme = None)
    
def vehicle_speed_per_day_component():
    st.markdown('#### Kecepatan Kendaraan per Jam')
    d = st.date_input("Pilih tanggal untuk ditampilkan:", key = 'vehicle_speed_per_day_by_date', format="DD/MM/YYYY")
    
    col = st.columns((1,1))
    
    with col[0]:
        waktu_awal = st.time_input("Dari jam:", value=None, key = 'vehicle_speed_per_day_time_start', step = 3600)
    
    with col[1]:
        waktu_akhir = st.time_input("Sampai jam", value=None, key = 'vehicle_speed_per_day_time_end', step = 3600)
    
    df = concatCSVtoDataframe(d, d)
    df = selectbyTimeframe(df, waktu_awal, waktu_akhir)
    chart_total, chart_by_category = vehicle_speed_per_day_chart(df)

    tab1, tab2 = st.tabs(["Rerata Keseluruhan", "Rerata per Kategori"])
    
    with tab1:
        st.altair_chart(chart_total, theme = None)
    
    with tab2:
        st.altair_chart(chart_by_category, theme = None)

@st.cache_resource    
def vehicle_speed_heatmap_chart(df):
    df['kecepatan'] = df['kecepatan'].abs()
    
    #Beberapa kendaraan ada yang terdeteksi sebagai dua atau lebih jenis kendaraan
    #Diubah menjadi satu jenis kendaraan, berdasarkan hasil modus jenis_kendaraan
    df['jenis_kendaraan'] = df['nomor_identifikasi'].map(df.groupby('nomor_identifikasi')['jenis_kendaraan']
                                                         .agg(lambda x: x.mode()[0]))
    
    df['waktu_terekam'] = pd.to_datetime(df['waktu_terekam'])
    
    df['tanggal'] = pd.to_datetime(df['waktu_terekam']).dt.date
    
    uniques = df.groupby(['tanggal', 'nomor_identifikasi']).nunique()
    
    #buang nomor_identifikasi yang terekam di kurang dari 3 frame
    uniques = uniques[uniques['waktu_terekam'].ge(3)]
    
    df = df[df['nomor_identifikasi'].isin(uniques.index.get_level_values('nomor_identifikasi'))]
    
    df['interval'] = df['waktu_terekam'].dt.floor('1h')
    df_mean_all = df[['tanggal', 'interval', 'kecepatan']].groupby(by=['tanggal', 'interval']).mean().round(2).reset_index()
    df_mean_all['interval'] = df_mean_all['interval'].dt.strftime("%H:%M")
    df_mean_all['tanggal'] = df_mean_all['tanggal'].astype(str)
    
    speed_domain = [0, 40, 42]
    color_range = ['green', 'green', 'red']
    
    a  = (alt.Chart(df_mean_all).mark_rect().encode(
        alt.X('interval:O').title('Jam'),
        alt.Y('tanggal:O').title('Tanggal'),
        #color = alt.condition('datum.kecepatan > 40', alt.value('red'), alt.value('green'))#.title('Rerata Kecepatan (km/jam)')
        color = alt.condition('datum.kecepatan >= 40', alt.value('red'), alt.Color('kecepatan').scale(domain = speed_domain, range = color_range)).title('Rerata Kecepatan (km/jam)')
    ))
    
    a = a.configure_axis(
        labelFontSize=15,
        titleFontSize=15
        ).properties(
        height=320,
        width=screen_width/2.5,
        ).interactive()
    
    return a

def vehicle_speed_heatmap_component():
    st.markdown('#### Heatmap Kecepatan Kendaraan (1 minggu)')
    
    col = st.columns((1,1))
    container = st.container(height=320, border = False)
    
    with col[0]:
        d_start = st.date_input("Dari tanggal:", key = 'vehicle_speed_heatmap_component_start_date', format="DD/MM/YYYY")
    
    with col[1]:
        d_end = st.date_input("Sampai tanggal (periode maksimal 7 hari):", key = 'vehicle_speed_heatmap_component_end_date', format="DD/MM/YYYY")
    
    if (d_end - d_start).days >= 7 :
        st.error('Periode yang dapat ditampilkan maksimal tujuh hari!')
    elif (d_end - d_start).days < 0:
        st.error('Tanggal awal harus lebih kecil dari tanggal akhir!')
    else:
        df = concatCSVtoDataframe(d_start, d_end)
        chart = vehicle_speed_heatmap_chart(df)
        #chart = vehicle_speed_heatmap_chart(df).properties(title = f"Heatmap Kecepatan Kendaraan").configure_title(
        #    fontSize=18,
        #    font='Arial',
        #    anchor='middle',
        #    color='black'
        #)
        with container:
            st.altair_chart(chart, theme = None)
    
def showInferenceImage():
    st.markdown('#### Hasil Deteksi')
    container = st.container(height=360, border=False)
    path = os.getcwd() + '\\'
    image_path = path + 'inference_result/current_frame.jpg'
    with container:
        if os.path.isfile(image_path):
            try:
                im1 = Image.open(image_path)
                st.image(im1)
            except UnidentifiedImageError:
                st.error('Kondisi gambar corrupt!')
        else:
            st.error('Gambar tidak tersedia!')
    
def selectbyTimeframe(df, time_start, time_end):
    df['waktu_terekam'] = pd.to_datetime(df['waktu_terekam'])
    df = df[(df['waktu_terekam'].dt.time >= time_start) & (df['waktu_terekam'].dt.time <= time_end)]
    return df
        
def validateDir(paths):
    all_vehicle_record_path = os.getcwd() + '\\' + 'vehicle_records'
    all_files = []
    
    #Mengambil list seluruh file di direktori vehicle_records
    for root, _, filenames in os.walk(all_vehicle_record_path):
        for file in filenames:
            all_files.append(os.path.join(root, file))
    
    #Intersection antara paths berdasarkan pilihan tanggal dengan path yang tersedia
    all_files_set = set(all_files)
    paths_set = set(paths)
    
    return list(all_files_set.intersection(paths_set))

#Jika kendaraan tidak bergerak, frame dimana kendaraan tersebut berhenti dibatasi hingga max 375 frame (15 detik saja)
#Kendaraan tidak bergerak kecepatannya antara -3.6, 0, 3.6
def filterIdleVehicle(df):
    df_unstable = df[(df['kecepatan'] >= -4) & (df['kecepatan'] <= 4)]
    df_unstable = df_unstable.groupby('nomor_identifikasi').head(375)
    df_stable = df[(df['kecepatan'] < -4) | (df['kecepatan'] > 4)]
    
    return pd.concat([df_unstable, df_stable])
    
def concatCSVtoDataframe(start_date, end_date):
    dates = []
    paths = []
    all_vehicle_record_path = os.getcwd() + '\\' + 'vehicle_records'
    df = pd.DataFrame()
    df[['waktu_terekam', 'nomor_identifikasi', 'jenis_kendaraan', 'kecepatan']] = None
    
    for i in range((end_date - start_date).days + 1):
        dates.append(start_date + pd.Timedelta(days=i))
    
    for date in dates:
        monthly_vehicle_record_path = all_vehicle_record_path + '\\' + '-'.join([str(date.month), str(date.year)])
        record_name = '-'.join([str(date.day), str(date.month), str(date.year)]) + '.csv'
        record_path = monthly_vehicle_record_path + '\\' + record_name
        
        paths.append(record_path)
    
    paths = validateDir(paths)
    
    if len(paths) > 0:
        df = pd.concat(map(pd.read_csv, paths), ignore_index=True)
        df = filterIdleVehicle(df)

        #Filter untuk menginclude kendaraan masuk/keluar kawasan berdasarkan arah kecepatan (kecepatan kendaraan arah kawasan adalah positif)
        if mode == "Arah Masuk Kawasan":
            kendaraan_masuk = df[df['kecepatan'] > 0]['nomor_identifikasi'].unique()
            df = df[df['nomor_identifikasi'].isin(kendaraan_masuk)]
        elif mode == "Arah Keluar Kawasan":
            kendaraan_keluar = df[df['kecepatan'] < 0]['nomor_identifikasi'].unique()
            df = df[df['nomor_identifikasi'].isin(kendaraan_keluar)]
        
    return df
    
#@st.fragment(run_every=30)
#def show_latest_data():
container = st.container()
col = st.columns((4, 4), gap='medium')

with container:
    screen_width = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
    with col[0]:
        vehicle_speed_heatmap_component()
        vehicle_count_per_day_component()
        weekly_component()
        
    with col[1]:
        vehicle_count_per_day_by_category_component()
        vehicle_speed_per_day_component()
        showInferenceImage()
    

#show_latest_data()
