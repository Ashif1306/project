# Midtrans Snap Payment Integration - Setup Guide

Panduan lengkap untuk mengonfigurasi integrasi pembayaran Midtrans Snap di project Django Commerce Kaloriz.

## Fitur yang Tersedia

- ✅ Integrasi Midtrans Snap (mode Sandbox dan Production)
- ✅ Popup pembayaran otomatis setelah klik Checkout
- ✅ Multiple payment methods: Credit Card, Bank Transfer, E-Wallets (GoPay, ShopeePay), QRIS, dll
- ✅ Webhook/notification handler untuk update status pembayaran
- ✅ Tracking transaksi pembayaran di admin
- ✅ Stock deduction otomatis setelah pembayaran berhasil
- ✅ Cart items clearing setelah payment confirmed

## Konfigurasi Awal

### 1. Setup Environment Variables

Copy file `.env.example` ke `.env` dan isi dengan credentials Midtrans Anda:

```bash
cp .env.example .env
```

Edit file `.env`:

```env
# Midtrans Credentials (get from Midtrans Dashboard)
MIDTRANS_MERCHANT_ID=your_merchant_id_here
MIDTRANS_CLIENT_KEY=your_client_key_here
MIDTRANS_SERVER_KEY=your_server_key_here
MIDTRANS_IS_PRODUCTION=False
```

**Catatan:**
- Gunakan credentials Sandbox untuk development/testing
- Gunakan credentials Production dan set `MIDTRANS_IS_PRODUCTION=True` untuk production
- Dapatkan credentials dari [Midtrans Dashboard](https://dashboard.midtrans.com/)

### 2. Verifikasi Payment Method di Admin

1. Akses Django Admin: `/admin/`
2. Buka menu **Core > Payment Methods**
3. Pastikan **Midtrans Snap** sudah aktif (is_active = True)
4. Jika belum ada, data migration sudah otomatis membuat record ini

### 3. Setup Notification URL di Midtrans Dashboard

Untuk menerima webhook dari Midtrans:

1. Login ke [Midtrans Dashboard](https://dashboard.midtrans.com/)
2. Pilih environment (Sandbox/Production)
3. Masuk ke **Settings > Configuration**
4. Set **Notification URL** ke:
   ```
   https://your-domain.com/payment/midtrans-notification/
   ```
5. Set **Finish Redirect URL** ke:
   ```
   https://your-domain.com/order/{order_id}/
   ```

**Untuk development lokal**, gunakan tools seperti [ngrok](https://ngrok.com/) untuk expose local server:
```bash
ngrok http 8000
```
Kemudian gunakan URL ngrok sebagai base URL di Midtrans Dashboard.

## Flow Pembayaran

### User Flow:

1. **Select Items** → User memilih produk di keranjang
2. **Checkout Address** → User memilih/input alamat pengiriman
3. **Select Payment** → User memilih "Midtrans Snap" sebagai metode pembayaran
4. **Review Order** → User mereview pesanan dan klik "Bayar Sekarang"
5. **Snap Popup** → Popup Midtrans Snap muncul otomatis
6. **Choose Payment** → User memilih metode pembayaran (Credit Card, Bank Transfer, dll)
7. **Payment Process** → User menyelesaikan pembayaran
8. **Redirect** → User diarahkan ke halaman detail order
9. **Status Update** → Status order otomatis update berdasarkan notifikasi Midtrans

### Technical Flow:

```
1. User clicks "Bayar Sekarang"
   ↓
2. Frontend calls: POST /payment/create-snap-token/
   ↓
3. Backend creates:
   - Order (status: pending)
   - OrderItems
   - Shipment record
   - PaymentTransaction
   - Calls Midtrans API untuk generate snap_token
   ↓
4. Frontend receives snap_token
   ↓
5. Frontend opens Snap popup: snap.pay(snapToken)
   ↓
6. User completes payment in Snap popup
   ↓
7. Midtrans sends notification to: /payment/midtrans-notification/
   ↓
8. Backend updates:
   - PaymentTransaction status
   - Order status
   - Deduct product stock (if payment success)
   - Clear cart items (if payment success)
   ↓
9. User sees updated order status in order detail page
```

## Endpoints yang Tersedia

### 1. Create Snap Token (Protected)
- **URL:** `/payment/create-snap-token/`
- **Method:** POST
- **Auth:** Login required
- **Description:** Generate Midtrans Snap token dan create order

### 2. Midtrans Notification (Public)
- **URL:** `/payment/midtrans-notification/`
- **Method:** POST
- **Auth:** CSRF exempt (called by Midtrans server)
- **Description:** Handle payment notification dari Midtrans

### 3. Check Payment Status (Protected)
- **URL:** `/payment/check-status/<order_number>/`
- **Method:** GET
- **Auth:** Login required
- **Description:** Check payment status dari Midtrans (untuk debugging)

## Status Mapping

### Transaction Status:

| Midtrans Status | Order Status | Action |
|----------------|--------------|--------|
| `pending` | pending | Wait for payment |
| `capture` (fraud: accept) | processing | Deduct stock, clear cart |
| `settlement` | processing | Deduct stock, clear cart |
| `deny` | cancelled | No action |
| `cancel` | cancelled | No action |
| `expire` | cancelled | No action |
| `failure` | cancelled | No action |

## Testing dengan Sandbox

Midtrans Sandbox menyediakan test credentials untuk berbagai payment methods:

### Test Credit Cards:

| Card Type | Number | CVV | Expiry |
|-----------|--------|-----|--------|
| Success | 4811 1111 1111 1114 | 123 | Any future date |
| Failure | 4911 1111 1111 1113 | 123 | Any future date |

### Test VA Numbers:

Setelah generate VA number, gunakan simulator di [Midtrans Sandbox Dashboard](https://simulator.sandbox.midtrans.com/bca/va/index)

### Test E-Wallets:

- GoPay: Use QR simulator in Sandbox
- ShopeePay: Auto-approve in Sandbox

Dokumentasi lengkap test credentials: https://docs.midtrans.com/en/technical-reference/sandbox-test

## Monitoring & Debugging

### Admin Dashboard:

1. **Payment Transactions:** `/admin/core/paymenttransaction/`
   - Lihat semua transaksi pembayaran
   - Check status transaksi
   - View response dari Midtrans

2. **Orders:** `/admin/core/order/`
   - Monitor order status
   - Lihat detail pembayaran per order

### Manual Status Check:

Untuk mengecek status pembayaran manual:
```
GET /payment/check-status/<order_number>/
```

### Logs:

Check Django console untuk error logs dan transaction info.

## Troubleshooting

### Popup Snap tidak muncul:
- Cek console browser untuk error
- Pastikan MIDTRANS_CLIENT_KEY sudah benar di .env
- Pastikan Snap SDK script loaded (check Network tab)

### Order created tapi status masih pending:
- Cek apakah notification URL sudah di-set di Midtrans Dashboard
- Verify signature key (check logs)
- Test notification manual via Midtrans Dashboard

### Stock tidak berkurang setelah payment:
- Pastikan notification dari Midtrans diterima
- Check transaction status: harus `settlement` atau `capture` (fraud: accept)
- Check logs di PaymentTransaction admin

### Production Checklist:
- [ ] Ganti credentials dengan Production credentials
- [ ] Set `MIDTRANS_IS_PRODUCTION=True`
- [ ] Update notification URL dengan production URL
- [ ] Test all payment methods di Production
- [ ] Monitor transactions via Midtrans Dashboard
- [ ] Setup proper error logging & monitoring

## Security Notes

- ⚠️ **JANGAN commit credentials ke Git**
- ⚠️ File `.env` sudah ada di `.gitignore`
- ⚠️ Gunakan environment variables untuk credentials
- ⚠️ Verification signature untuk semua notifications dari Midtrans
- ⚠️ HTTPS required untuk production

## Support

- Midtrans Documentation: https://docs.midtrans.com/
- Midtrans Dashboard: https://dashboard.midtrans.com/
- Midtrans Support: support@midtrans.com

## Version

- Django: 5.2.8
- midtransclient: 1.4.2
- Integration Date: 2025-11-06
