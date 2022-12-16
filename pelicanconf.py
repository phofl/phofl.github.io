AUTHOR = 'Patrick Hoefler'
SITENAME = 'Patrick Hoefler'
SITEURL = ''

TIMEZONE = 'Europe/Berlin'
DEFAULT_LANG = 'en'

PATH = 'content'

STATIC_PATHS = [
    "images/",
    "pages/",
]

# Set the article URL
ARTICLE_URL = 'blog/{date:%Y}/{date:%m}/{date:%d}/{slug}/'
ARTICLE_SAVE_AS = 'blog/{date:%Y}/{date:%m}/{date:%d}/{slug}/index.html'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Plugins
PLUGIN_PATHS = ['./plugins/pelican-ipynd', './plugins/pelican-plugins']
PLUGINS = [
    'summary', # auto-summarizing articles
]

MARKDOWN = {
    'extension_configs': {
        'markdown.extensions.codehilite': {'css_class': 'highlight'},
        'markdown.extensions.extra': {},
        'markdown.extensions.meta': {},
        'markdown.extensions.toc': {'permalink': True},
    },
    'output_format': 'html5',
}

# Theme
#THEME = "pelican-themes/pelican-hss"
THEME = './theme'

ABOUT_PAGE = '/pages/about.html'
GITHUB_USERNAME = 'phofl'
AUTHOR_BLOG = 'http://phofl.github.io'


# Social widget
SOCIAL = (('github', 'https://github.com/phofl/'),)

DEFAULT_PAGINATION = 10
