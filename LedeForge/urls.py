"""LedeForge URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin

from Container.urls import container_urlpatterns
from Repository.urls import repository_urlpatterns
from LedeForge.views import IndexView, TerminalView

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^container/', include(container_urlpatterns)),
    url(r'^repository/', include(repository_urlpatterns)),
    url(r'^terminal/(?P<terminal_type>[a-z]+)/(?P<terminal_name>[a-f0-9]+)/$', TerminalView.as_view(), name='terminal'),
    url(r'^$', IndexView.as_view())
]
