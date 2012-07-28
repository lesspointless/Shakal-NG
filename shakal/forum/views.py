# -*- coding: utf-8 -*-

from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.template import RequestContext
from django.views.generic import CreateView
from datetime import datetime
from forms import TopicForm, TopicLoggedForm
from models import Section, Topic

def overview(request, section = None, page = 1):
	topics = Topic.objects
	if section is not None:
		section = get_object_or_404(Section, slug = section)
		topics = topics.filter(section = section)

	context = {
		'forum': topics.order_by('-pk').all(),
		'section': section,
		'pagenum': page,
		'sections': Section.objects.all()
	}
	return TemplateResponse(request, "forum/topic_list.html", RequestContext(request, context))


def topic_detail(request, pk):
	topic = get_object_or_404(Topic, pk = pk)
	context = {
		'topic': topic
	}
	return TemplateResponse(request, "forum/topic_detail.html", RequestContext(request, context))


class TopicCreateView(CreateView):
	model = Topic
	template_name = 'forum/topic_create.html'

	def get_form_class(self):
		if self.request.user.is_authenticated():
			return TopicLoggedForm
		else:
			return TopicForm

	def form_valid(self, form):
		topic = form.save(commit = False)
		topic.time = datetime.now()
		if self.request.user.is_authenticated():
			if self.request.user.get_full_name():
				topic.username = self.request.user.get_full_name()
			else:
				topic.username = self.request.user.username
			topic.user = self.request.user
		if not 'create' in self.request.POST:
			return self.render_to_response(self.get_context_data(form = form, topic = topic, valid = True))
		return super(TopicCreateView, self).form_valid(form)
