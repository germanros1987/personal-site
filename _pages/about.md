---
permalink: /
title: "German Ros, Ph.D"
excerpt: "About me"
author_profile: true
redirect_from:
  - /about/
  - /about.html
---
{% include base_path %}

{% include bio.html %}

News
------

{% include dated-list.html items=site.data.updates.news kind="news" %}


Recent Talks
------
{% include dated-list.html items=site.data.updates.talks kind="talks" %}


Academic Service
------

Chair and organizer of international workshops and challenges.

{% include dated-list.html items=site.data.academic_service kind="service" %}


Publications
------

{% include scholar-publications.html %}
