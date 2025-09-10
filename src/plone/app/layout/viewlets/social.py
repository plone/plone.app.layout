from plone.app.layout.viewlets.common import TitleViewlet
from plone.base.interfaces import ISocialMediaSchema
from plone.base.interfaces.syndication import IFeedItem
from plone.memoize.view import memoize
from plone.registry.interfaces import IRegistry
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.browser.syndication.adapters import BaseItem
from Products.CMFPlone.browser.syndication.adapters import FolderFeed
from Products.CMFPlone.utils import getSiteLogo
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.component.hooks import getSite

import logging


logger = logging.getLogger("plone.app.layout")


class SocialTagsViewlet(TitleViewlet):
    social_image_scale = "great"

    def head_tag_filter(self, value):
        if not isinstance(value, dict):
            return
        return "itemprop" not in value

    def body_tag_filter(self, value):
        if not isinstance(value, dict):
            return
        return "itemprop" in value

    @property
    def tags(self):
        # Do not show items with 'itemprop'.
        return list(filter(self.head_tag_filter, self._get_tags()))

    @property
    def body_tags(self):
        # Show only items without 'itemprop'.
        return list(filter(self.body_tag_filter, self._get_tags()))

    @memoize
    def _get_tags(self):
        site = getSite()
        registry = getUtility(IRegistry)
        settings = registry.forInterface(
            ISocialMediaSchema, prefix="plone", check=False
        )

        if not settings.share_social_data:
            return []

        portal_membership = getToolByName(site, "portal_membership")
        is_anonymous = bool(portal_membership.isAnonymousUser())
        if not is_anonymous:
            return []

        tags = [
            dict(itemprop="name", content=self.page_title),
            dict(name="twitter:card", content="summary"),
            dict(property="og:site_name", content=self.site_title_setting),
            dict(property="og:title", content=self.page_title),
            dict(property="og:type", content="website"),
        ]
        if settings.twitter_username:
            tags.append(
                dict(
                    name="twitter:site",
                    content="@" + settings.twitter_username.lstrip("@"),
                )
            )
        if settings.facebook_app_id:
            tags.append(dict(property="fb:app_id", content=settings.facebook_app_id))
        if settings.facebook_username:
            tags.append(
                dict(
                    property="og:article:publisher",
                    content="https://www.facebook.com/" + settings.facebook_username,
                )
            )

        # reuse syndication since that packages the data
        # the way we'd prefer likely
        feed = FolderFeed(site)
        item = queryMultiAdapter((self.context, feed), IFeedItem, default=None)
        if item is None:
            item = BaseItem(self.context, feed)

        tags.extend(
            [
                dict(itemprop="description", content=item.description),
                dict(itemprop="url", content=item.link),
                dict(property="og:description", content=item.description),
                dict(property="og:url", content=item.link),
            ]
        )

        found_image = False
        if item.has_enclosure and item.file_length > 0:
            if item.file_type.startswith("image"):
                image = None
                scales = self.context.restrictedTraverse("@@images", None)
                if scales:
                    try:
                        image = scales.scale("image", scale=self.social_image_scale)
                    except Exception as e:
                        logger.exception(e)
                if image:
                    tags.extend(
                        [
                            dict(property="og:image", content=image.url),
                            dict(property="og:image:width", content=image.width),
                            dict(property="og:image:height", content=image.height),
                            dict(itemprop="image", content=image.url),
                            dict(property="og:image:type", content=item.file_type),
                        ]
                    )
                    found_image = True
            elif (
                item.file_type.startswith("video")
                or item.file_type == "application/x-shockwave-flash"
            ):
                tags.extend(
                    [
                        dict(property="og:video", content=item.file_url),
                        dict(property="og:video:type", content=item.file_type),
                    ]
                )
            elif item.file_type.startswith("audio"):
                tags.extend(
                    [
                        dict(property="og:audio", content=item.file_url),
                        dict(property="og:audio:type", content=item.file_type),
                    ]
                )

        if not found_image:
            url, mime_type = getSiteLogo(include_type=True)
            tags.extend(
                [
                    dict(property="og:image", content=url),
                    dict(itemprop="image", content=url),
                    dict(property="og:image:type", content=mime_type),
                ]
            )
        return tags
