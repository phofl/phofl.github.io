#!/usr/bin/env python
# -*- coding: utf-8 -*- #

AUTHOR = 'Patrick Hoefler'
SITENAME = 'Patrick Hoefler'
SITEURL = ''

TIMEZONE = 'Europe/Berlin'
DEFAULT_LANG = 'en'

PATH = 'content'


# Theme
THEME = './theme'
CSS_FILE = 'main.css'
STATIC_PATHS = [
    'images/',
    'pages/',
    'extra/',
]

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None
FEED_RSS = "feed"

CUSTOM_CSS_URL = '/docs/extra/custom.css'
DEFAULT_PAGINATION = 10
RELATIVE_URLS = True
EXTRA_PATH_METADATA = {
    'extra/custom.css': {'path': 'docs/extra/custom.css'},
}
MARKDOWN = {
    'extension_configs': {
        'markdown.extensions.extra': {},
        'markdown.extensions.meta': {},
        'markdown.extensions.toc': {},
    },
    'output_format': 'html5',
}
ABOUT_PAGE = '/pages/about.html'
GITHUB_USERNAME = 'phofl'
AUTHOR_BLOG = 'https://phofl.github.io'


# Social widget
SOCIAL = (
    ('github', 'https://github.com/phofl/'),
    ('linkedin', 'https://www.linkedin.com/in/patrick-hoefler/'),
    ('mail', 'mailto:patrick_hoefler@gmx.net'),
)
