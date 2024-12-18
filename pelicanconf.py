#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

# run like:
# make devserver
# make rsync_upload
# Uncomment following line if you want document-relative URLs when developing locally
RELATIVE_URLS = True

# NOTE because we're using `Makefile` some of these settings may not apply. If
# there is something strange, assume the makefile takes priority.

AUTHOR = 'Jared Candelaria'
SITENAME = 'Esoteric Nonsense and Other Ramblings'
SITESUBNAME = 'A website from Jared Candelaria'
SITEURL = 'https://calabi-yau.space/blog'
OUTPUT_PATH = 'output/blog'
# relative to SITEURL
SITEIMAGE = 'images/badman.jpg'

TIMEZONE = 'US/Pacific'

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Do not format the summary field.
FORMATTED_FIELDS = []

# Do not process html files
READERS = {'html': None}

# Do not mess with data/
STATIC_PATHS = ['data', 'images', 'extra']

# Assume draft by default
#DEFAULT_METADATA = {'status': 'draft'}

# This is pretty hacky. We *KNOW* that our output path is /blog but these files
# are "extra" in the sense that they sit OUTSIDE of that path. We escape our
# confinement of /blog by placing these in the parent directory. This has
# implication in how we build and cleanup as well.
EXTRA_PATH_METADATA = {
    'extra/robots.txt': {'path': '../robots.txt'},
    'extra/favicon.ico': {'path': '../favicon.ico'},
}


# plugins

## https://github.com/getpelican/pelican-plugins/tree/master/extract_toc
MARKDOWN = {
    'extension_configs': {
        'markdown.extensions.toc': {
            'title': "Table of Contents",
        },
        'markdown.extensions.codehilite': {
            'css_class': "highlight",
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
