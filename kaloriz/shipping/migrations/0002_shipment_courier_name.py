from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shipping', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='shipment',
            name='courier_name',
            field=models.CharField(
                blank=True,
                choices=[
                    ('JNE', 'JNE'),
                    ('JNT', 'J&T Express'),
                    ('SICEPAT', 'SiCepat Ekspres'),
                    ('POS', 'Pos Indonesia'),
                    ('TIKI', 'TIKI'),
                    ('LION', 'Lion Parcel'),
                    ('ANTERAJA', 'Anteraja'),
                    ('SAPX', 'SAPX Express'),
                    ('GOSEND', 'GoSend'),
                    ('GRAB', 'GrabExpress'),
                ],
                help_text='Kurir yang digunakan untuk pengiriman',
                max_length=20,
                verbose_name='Kurir',
            ),
        ),
    ]
