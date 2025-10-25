from django import forms
from .models import Address, District


class AddressForm(forms.ModelForm):
    """
    Form untuk alamat pengiriman di checkout
    """
    class Meta:
        model = Address
        fields = ['full_name', 'phone', 'street', 'district', 'postal_code', 'is_default']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nama lengkap penerima'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '08123456789'
            }),
            'street': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Alamat lengkap (nama jalan, nomor rumah, RT/RW, dll)'
            }),
            'district': forms.Select(attrs={
                'class': 'form-control',
                'id': 'district-select'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '90xxx'
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'full_name': 'Nama Lengkap',
            'phone': 'Nomor Telepon',
            'street': 'Alamat / Jalan',
            'district': 'Kecamatan',
            'postal_code': 'Kode Pos',
            'is_default': 'Jadikan alamat utama',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active districts
        self.fields['district'].queryset = District.objects.filter(is_active=True)

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
