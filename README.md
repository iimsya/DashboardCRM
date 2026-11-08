# Sora CRM Dashboard

Dashboard CRM interaktif berbasis Streamlit untuk dataset Brazilian E-Commerce
Olist. File CSV sumber berada di `data/raw/`.

## Menjalankan aplikasi

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Struktur

- `app.py`: halaman overview.
- `pages/`: halaman pelanggan/geografi, loyalitas/risiko, produk/strategi, dan
  analisis/jawaban atas pertanyaan CRM.
- `src/data_loader.py`: pemuatan serta validasi file dan relasi CSV.
- `src/analysis.py`: agregasi pesanan, metrik pelanggan, dan segmentasi.
- `src/ui.py`: gaya, filter, format mata uang, dan komponen bersama.
- `assets/sora_logo.svg`: logo dashboard yang tampil di atas navigasi.
- `data/raw/`: file CSV sumber Olist.
- `tests/`: pengujian pengolahan metrik inti.
- `.streamlit/config.toml`: tema warna Streamlit.

## Definisi analisis

- KPI nilai transaksi menggunakan jumlah pembayaran untuk pesanan terkirim.
- Satu baris fakta merepresentasikan satu pesanan; pembayaran, item, dan ulasan
  diringkas lebih dahulu agar join tidak menggandakan nilai.
- Identitas lintas transaksi menggunakan `customer_unique_id`.
- Risiko tidak aktif dihitung dari hari sejak pembelian terakhir sampai tanggal
  transaksi terakhir yang tersedia di dataset, dengan ambang lebih dari 180 hari.
- Dataset berakhir pada 2018 dan tidak mencatat sumber akuisisi pemasaran.
  Informasi lokasi pelanggan bukan atribusi kanal iklan.
