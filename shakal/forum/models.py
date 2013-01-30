# -*- coding: utf-8 -*-

from attachment.models import Attachment
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import permalink
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from datetime import datetime, timedelta
from shakal.threaded_comments.models import RootHeader, ThreadedComment

class Section(models.Model):
	name = models.CharField(max_length = 255, verbose_name = _('name'))
	slug = models.SlugField(unique = True)
	description = models.TextField(verbose_name = _('description'))

	def clean(self):
		slug_num = None
		try:
			slug_num = int(self.slug)
		except:
			pass
		if slug_num is not None:
			raise ValidationError(_('Numeric slug values are not allowed'))

	@permalink
	def get_absolute_url(self):
		return ('forum:section', None, {'section': self.slug})

	def __unicode__(self):
		return self.name

	class Meta:
		verbose_name = _('section')
		verbose_name_plural = _('sections')


class TopicManager(models.Manager):
	def get_query_set(self):
		return super(TopicManager, self).get_query_set().select_related('user', 'section')

	def topics(self):
		return self.get_query_set().filter(is_removed = False)


class TopicListManager(models.Manager):
	def get_query_set(self):
		return super(TopicListManager, self).get_query_set().filter(is_removed = False)

	def newest_topics(self, section = None):
		queryset = self.get_query_set()
		if not section is None:
			queryset = queryset.filter(section = section)
		queryset = queryset.order_by('-pk')
		return queryset

	def newest_comments(self):
		queryset = self.get_query_set()
		queryset = queryset.filter(comments_header__last_comment__gt = datetime.now() - timedelta(30))
		queryset = queryset.order_by("-comments_header__last_comment")
		return queryset

	def no_comments(self):
		queryset = self.get_query_set()
		queryset = queryset.filter(comments_header__comment_count = 0)
		queryset = queryset.filter(comments_header__last_comment__gt = datetime.now() - timedelta(60))
		queryset = queryset.order_by("-id")
		return queryset

	def most_commented(self):
		queryset = self.get_query_set()
		queryset = queryset.filter(comments_header__last_comment__gt = datetime.now() - timedelta(30))
		queryset = queryset.order_by("-comments_header__comment_count")
		return queryset


class Topic(models.Model):
	objects = TopicManager()
	topics = TopicListManager()

	section = models.ForeignKey(Section, verbose_name = _('section'))
	title = models.CharField(max_length = 100, verbose_name = _('subject'))
	text = models.TextField(verbose_name = _('text'))
	created = models.DateTimeField(verbose_name = _('time'))
	updated = models.DateTimeField(editable = False)
	authors_name = models.CharField(max_length = 50, blank = False, verbose_name = _('authors name'))
	author = models.ForeignKey(User, blank = True, null = True, verbose_name = _('author'))
	comments_header = generic.GenericRelation(RootHeader)
	breadcrumb_label = _('forum')
	attachments = generic.GenericRelation(Attachment)
	is_removed = models.BooleanField(default = False, verbose_name = u'vymazané')
	is_resolved = models.BooleanField(default = False)

	def get_tags(self):
		tags = []
		if self.is_removed:
			tags.append('deleted')
		if self.is_resolved:
			tags.append('resolved')
		if tags:
			return u' ' + u' '.join(tags)
		else:
			return u''

	def get_attachments(self):
		return self.attachments.all()

	def save(self, *args, **kwargs):
		self.updated = datetime.now()
		if not self.id:
			self.created = self.updated
		return super(Topic, self).save(*args, **kwargs)

	def get_authors_name(self):
		if self.author:
			if self.author.get_full_name():
				return self.author.get_full_name()
			else:
				return self.author.username
		else:
			return self.authors_name
	get_authors_name.short_description = _('user name')

	@permalink
	def get_absolute_url(self):
		return ('forum:topic-detail', None, {'pk': self.pk})

	@permalink
	def get_list_url(self):
		return ('forum:overview', None, None)

	def __unicode__(self):
		return self.title

	class Meta:
		verbose_name = _('topic')
		verbose_name_plural = _('topics')


def update_comments_header(sender, instance, **kwargs):
	root, created = ThreadedComment.objects.get_root_comment(ctype = ContentType.objects.get_for_model(Topic), object_pk = instance.pk)
	if created:
		root.last_comment = instance.created
	root.is_removed = instance.is_removed
	root.save()

post_save.connect(update_comments_header, sender = Topic)
