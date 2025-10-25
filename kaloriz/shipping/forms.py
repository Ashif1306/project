from django import forms
from .models import Address, District


class AddressForm(forms.ModelForm):
    """
    Form untuk alamat pengiriman dengan dukungan RajaOngkir API
    """
    class Meta:
        model = Address
        fields = [
            'full_name', 'phone', 'address_line',
            'province_name', 'city_name', 'subdistrict_name', 'destination_subdistrict_id',
            'postal_code', 'is_primary',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nama lengkap penerima'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '08123456789'
            }),
            'address_line': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Alamat lengkap (nama jalan, nomor rumah, RT/RW, dll)'
            }),
            'province_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sulawesi Selatan',
                'readonly': 'readonly'
            }),
            'city_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Makassar'
            }),
            'subdistrict_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contoh: Panakkukang'
            }),
            'destination_subdistrict_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contoh: 7371100'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '90xxx'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'full_name': 'Nama Lengkap',
            'phone': 'Nomor Telepon',
            'address_line': 'Alamat / Jalan',
            'province_name': 'Provinsi',
            'city_name': 'Kota',
            'subdistrict_name': 'Kecamatan',
            'destination_subdistrict_id': 'ID Kecamatan (RajaOngkir)',
            'postal_code': 'Kode Pos',
            'is_primary': 'Jadikan alamat utama',
        }
        help_texts = {
            'destination_subdistrict_id': 'Masukkan ID kecamatan tujuan. (Nanti bisa diisi otomatis setelah integrasi API.)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default province to Sulawesi Selatan
        if not self.instance.pk or not self.instance.province_name:
            self.fields['province_name'].initial = 'Sulawesi Selatan'

    def clean_phone(self):
        """
        Validasi nomor telepon Indonesia
        """
        phone = self.cleaned_data.get('phone')

        # Normalize phone number
        if phone:
            phone = phone.strip().replace(' ', '').replace('-', '')

            # Validate format
            if not phone.startswith(('08', '+62', '62')):
                raise forms.ValidationError(
                    'Nomor telepon harus dimulai dengan 08, +62, atau 62'
                )

            # Validate length
            if phone.startswith('08'):
                if len(phone) < 10 or len(phone) > 13:
                    raise forms.ValidationError(
                        'Nomor telepon tidak valid (harus 10-13 digit)'
                    )
            elif phone.startswith('+62'):
                if len(phone) < 12 or len(phone) > 15:
                    raise forms.ValidationError(
                        'Nomor telepon tidak valid'
                    )

        return phone

    def clean_postal_code(self):
        """
        Validasi kode pos Makassar (90xxx)
        """
        postal_code = self.cleaned_data.get('postal_code')

        if postal_code:
            # Remove any spaces
            postal_code = postal_code.strip()

            # Check if it's numeric
            if not postal_code.isdigit():
                raise forms.ValidationError('Kode pos harus berupa angka')

            # Check if it starts with 90 (Makassar)
            if not postal_code.startswith('90'):
                raise forms.ValidationError(
                    'Kode pos harus dimulai dengan 90 (Makassar)'
                )

            # Check length
            if len(postal_code) != 5:
                raise forms.ValidationError('Kode pos harus 5 digit')

        return postal_code
