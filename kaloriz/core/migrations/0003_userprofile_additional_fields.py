from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='occupation',
            field=models.CharField(blank=True, max_length=150, verbose_name='Pekerjaan'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='additional_info',
            field=models.TextField(blank=True, verbose_name='Informasi Tambahan'),
        ),
    ]
