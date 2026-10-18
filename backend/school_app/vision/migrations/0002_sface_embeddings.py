from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('vision', '0001_initial')]

    operations = [
        migrations.AddField(model_name='facesample', name='embedding',
                            field=models.BinaryField(null=True)),
        migrations.AddField(model_name='facesample', name='model_key',
                            field=models.CharField(max_length=64, blank=True, default='')),
        migrations.AddField(model_name='visionscan', name='model_key',
                            field=models.CharField(max_length=64, default='lbph')),
        migrations.AddField(model_name='visionscan', name='cosine_score',
                            field=models.FloatField(null=True)),
    ]
