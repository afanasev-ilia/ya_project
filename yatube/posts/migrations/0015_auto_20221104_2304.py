# Generated by Django 2.2.16 on 2022-11-04 20:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0014_auto_20221031_2300'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='follow',
            options={
                'default_related_name': 'follow',
                'verbose_name': 'подписчик',
                'verbose_name_plural': 'подписчики',
            },
        ),
        migrations.AddField(
            model_name='comment',
            name='modified',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='post',
            name='modified',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='comment',
            name='created',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='post',
            name='created',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
