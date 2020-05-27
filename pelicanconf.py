#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

# Uncomment following line if you want document-relative URLs when developing locally
RELATIVE_URLS = True

AUTHOR = 'Jared Candelaria'
SITENAME = 'Esoteric Nonsense and Other Ramblings'
SITESUBNAME = 'A website from Jared Candelaria'
SITEURL = 'http://calabi-yau.space/blog'

TIMEZONE = 'US/Pacific'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# plugins

## https://github.com/getpelican/pelican-plugins/tree/master/extract_toc
MARKDOWN = {
    'extension_configs': {
        'markdown.extensions.toc': {
            'title': "Table of Contents",
        },
    },
}

# Blogroll
LINKS = ()
         #('Python.org', 'http://python.org/'),

# Social widget
SOCIAL = ()
          #('Another social link', '#'),)

DEFAULT_PAGINATION = False

## My settings

THEME = "themes/my_theme"

# Disable the menu
# Don't display files in pages/ in the menu
DISPLAY_PAGES_ON_MENU = False
# Don't display categories in the menu
DISPLAY_CATEGORIES_ON_MENU = False
