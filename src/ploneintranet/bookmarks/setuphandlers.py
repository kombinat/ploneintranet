# coding=utf-8
from logging import getLogger
from plone import api

logger = getLogger()


def post_default(context):
    ''' Actions needed after importing
    the ploneintranet.bookmarks:default profile
    '''
    portal = api.portal.get()
    apps = portal.apps
    if 'bookmarks' not in apps:
        api.content.create(
            container=apps,
            type='ploneintranet.layout.app',
            title=u'Bookmarks',
            id='bookmarks',
            safe_id=False,
            app='@@app-bookmarks',
        )

    app = apps.bookmarks
    if api.content.get_state(app) == 'published':
        return
    try:
        api.content.transition(app, to_state='published')
    except:
        logger.exception('Cannot publish the app: %r', app)
