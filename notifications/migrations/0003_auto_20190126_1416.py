# Generated by Django 2.1 on 2019-01-26 13:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		('contenttypes', '0002_remove_content_type_name'),
		('notifications', '0002_auto_20170603_1644'),
	]

	operations = [
		migrations.AddField(
			model_name='event',
			name='linked_id',
			field=models.PositiveIntegerField(blank=True, null=True),
		),
		migrations.AddField(
			model_name='event',
			name='linked_type',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='contenttypes.ContentType'),
		),
	]
