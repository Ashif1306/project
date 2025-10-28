from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import UserProfile
from catalog.models import Testimonial


class CustomUserRegistrationForm(UserCreationForm):
    """Custom registration form with additional fields"""

    # Basic fields
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label='Nama Lengkap',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masukkan nama lengkap Anda'
        })
    )

    email = forms.EmailField(
        required=True,
        label='E-mail',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'contoh@email.com'
        })
    )

    phone = forms.CharField(
        max_length=20,
        required=True,
        label='Nomor Telepon',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '08xxxxxxxxxx'
        })
    )

    birth_date = forms.DateField(
        required=True,
        label='Tanggal Lahir',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    # Password fields (inherited from UserCreationForm but customized)
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masukkan password'
        })
    )

    password2 = forms.CharField(
        label='Konfirmasi Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masukkan ulang password'
        })
    )

    # Terms and conditions
    agree_to_terms = forms.BooleanField(
        required=True,
        label='Saya menyetujui syarat dan ketentuan',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'email', 'phone', 'birth_date', 'password1', 'password2', 'agree_to_terms']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove username field requirement, we'll use email as username
        if 'username' in self.fields:
            self.fields.pop('username')

    def clean_email(self):
        """Validate that email is unique"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email ini sudah terdaftar.')
        return email

    def clean_phone(self):
        """Validate phone number"""
        phone = self.cleaned_data.get('phone')

        # Check if phone starts with 0 or +62
        if not (phone.startswith('0') or phone.startswith('+62')):
            raise ValidationError('Nomor telepon harus dimulai dengan 0 atau +62')

        # Check if phone already exists
        if UserProfile.objects.filter(phone=phone).exists():
            raise ValidationError('Nomor telepon ini sudah terdaftar.')

        return phone

    def clean_birth_date(self):
        """Validate birth date"""
        from datetime import date
        birth_date = self.cleaned_data.get('birth_date')

        if birth_date:
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

            if age < 13:
                raise ValidationError('Anda harus berusia minimal 13 tahun untuk mendaftar.')

            if birth_date > today:
                raise ValidationError('Tanggal lahir tidak valid.')

        return birth_date

    def save(self, commit=True):
        """Save user and create profile with additional fields"""
        # Create user with email as username
        email = self.cleaned_data['email']
        user = User(
            username=email,  # Use email as username
            email=email,
            first_name=self.cleaned_data['first_name']
        )
        user.set_password(self.cleaned_data['password1'])

        if commit:
            user.save()

            # Create user profile with additional fields
            UserProfile.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                birth_date=self.cleaned_data['birth_date']
            )

        return user


class TestimonialForm(forms.ModelForm):
    """Form for customers to submit product testimonials."""

    class Meta:
        model = Testimonial
        fields = ['rating', 'review', 'photo']
        widgets = {
            'rating': forms.Select(
                attrs={
                    'class': 'custom-select custom-select-sm',
                    'required': True,
                }
            ),
            'review': forms.Textarea(
                attrs={
                    'class': 'form-control form-control-sm',
                    'rows': 3,
                    'placeholder': 'Ceritakan pengalaman Anda menggunakan produk ini',
                    'required': True,
                }
            ),
            'photo': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control-file',
                    'accept': 'image/*',
                }
            ),
        }
        labels = {
            'rating': 'Rating',
            'review': 'Ulasan',
            'photo': 'Foto (Opsional)',
        }

