# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from simple.views import *


urlpatterns = patterns(
    '',
    url(r'^$', MyInstanceList.as_view(), kwargs={'host_id': 1}, name='my_instance_list'),
    url(r'^create/$', CreateInstanceFromTemplate.as_view(), kwargs={'host_id': 1}, name='create_instance'),
)
