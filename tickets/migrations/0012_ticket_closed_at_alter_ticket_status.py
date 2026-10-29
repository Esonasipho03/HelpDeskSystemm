from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0011_ittask'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='closed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='ticket',
            name='status',
            field=models.CharField(choices=[('Open', 'Open'), ('Assigned', 'Assigned'), ('In Progress', 'In Progress'), ('Pending', 'Pending'), ('Resolved', 'Resolved'), ('Closed', 'Closed')], default='Open', max_length=20),
        ),
    ]
