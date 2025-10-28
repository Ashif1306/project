from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_initial'),
        ('catalog', '0003_coupon_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='testimonial',
            name='order_item',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='testimonial',
                to='core.orderitem',
                verbose_name='Item Pesanan',
            ),
        ),
        migrations.AlterField(
            model_name='testimonial',
            name='review',
            field=models.TextField(blank=True, verbose_name='Ulasan'),
        ),
    ]
