# -*- coding: utf-8 -*-
from Acquisition import Explicit
from BTrees import OOBTree
from interfaces import INetworkGraph
from persistent import Persistent
from zope.interface import implements
import logging

logger = logging.getLogger('ploneintranet.network')


class NetworkGraph(Persistent, Explicit):
    """Stores a social network graph of users
    following/unfollowing or liking/unliking or tagging/untagging
    item_id users, content objects, status updates, tags.

    All references are resolvable, permanently stable, string ids.
    - StatusUpdates: a str() cast of status.id.
    - content: a uuid on the content.
    - users: a stable userid (not a changeable email)
    - tags: merging or renaming tags requires migrating the tag storage

    Return values are BTrees.OOBTree.OOTreeSet iterables.
    """

    implements(INetworkGraph)

    # These statics define the data storage schema "item_type" axes.
    # If you change them you need to carefully migrate the data storage
    # for existing users
    supported_follow_types = ("user", "content", "tag")
    supported_like_types = ("content", "update")
    supported_tag_types = ("user", "content")

    def __init__(self, context=None):
        """
        Set up storage for personalized data structures.

        FOLLOW: users can follow eachother, or content etc.
        ---------------------------------------------------

        _following["user"][userid] = (userid, userid, ...)
        _followers["user"][userid] = (userid, userid, ...)

        Other follow types can be switched on here but
        are not used anywhere yet.

        LIKE: users can like content or statusupdates
        ---------------------------------------------

        _likes["content"][userid] = (uuid, uuid, ...)
        _liked["content"][uuid] = (userid, userid, ...)

        _likes["update"][userid] = (statusid, statusid, ...)
        _liked["update"][statusid] = (userid, userid, ...)

        TAG: users can apply personal tags on anything.
        -----------------------------------------------

        Not yet implemented, and more complex than following or liking
        since tagging is a 3-way relation (subject, tags, object)

        Endorsements can be implemented as users tagging item_id users.

        supported_tag_types = ("user", "content", "update")

        Objects tagged by a user:
        _tagged[userid] = {tag: {type: ids}}
        _tagged[userid][tag] = {type: ids}
        _tagged[userid][tag]["user"] = (userid, userid, ...)
        _tagged[userid][tag]["content"] = (uuid, uuid, ...)

        Users that tagged an object:
        _tagger[item_type][id] = {tag: userids}
        _tagger["user"][userid][tag] = (userid, userid, ...)
        _tagger["content"][uuid][tag] = (userid, userid, ...)

        Tags applied by a user:
        _tags[user_id] = {item_type: item_id: (tag, tag,...)}
        _tags[user_id]["user"][userid] = (tag, tag, ...)
        _tags[user_id]["content"][uuid] = (tag, tag, ...)

        Find objects by tag: (and the users who applied that tag)
        _all[tag] = {item_type: {item_id: (userid, userid)}
        _all[tag]["user"][user_id] = (userid, userid, ...)
        _all[tag]["content"][uuid] = (userid, userid, ...)

        """

        # following
        self._following = OOBTree.OOBTree()
        self._followers = OOBTree.OOBTree()
        for item_type in self.supported_follow_types:
            self._following[item_type] = OOBTree.OOBTree()
            self._followers[item_type] = OOBTree.OOBTree()

        # like
        self._likes = OOBTree.OOBTree()
        self._liked = OOBTree.OOBTree()
        for item_type in self.supported_like_types:
            self._likes[item_type] = OOBTree.OOBTree()
            self._liked[item_type] = OOBTree.OOBTree()

        # tags
        self._tagged = OOBTree.OOBTree()
        self._tagger = OOBTree.OOBTree()
        self._tags = OOBTree.OOBTree()
        self._all = OOBTree.OOBTree()
        for item_type in self.supported_tag_types:
            self._tagger[item_type] = OOBTree.OOBTree()
        # more initialization on the fly in self.tag()

    # needed in suite/setuphandlers
    clear = __init__

    # following API

    def follow(self, item_type, user_id, item_id):
        """User <user_id> subscribes to <item_type> <item_id>"""
        assert(item_type in self.supported_follow_types)
        assert(user_id == str(user_id))
        assert(item_id == str(item_id))
        # insert user if not exists
        self._following[item_type].insert(user_id, OOBTree.OOTreeSet())
        self._followers[item_type].insert(item_id, OOBTree.OOTreeSet())
        # add follow subscription
        self._following[item_type][user_id].insert(item_id)
        self._followers[item_type][item_id].insert(user_id)

    def unfollow(self, item_type, user_id, item_id):
        """User <user_id> unsubscribes from <item_type> <item_id>"""
        assert(item_type in self.supported_follow_types)
        assert(user_id == str(user_id))
        assert(item_id == str(item_id))
        try:
            self._following[item_type][user_id].remove(item_id)
        except KeyError:
            pass
        try:
            self._followers[item_type][item_id].remove(user_id)
        except KeyError:
            pass

    def get_following(self, item_type, user_id):
        """List all <item_type> that <user_id> subscribes to"""
        assert(item_type in self.supported_follow_types)
        assert(user_id == str(user_id))
        try:
            return self._following[item_type][user_id]
        except KeyError:
            return ()

    def get_followers(self, item_type, item_id):
        """List all users that subscribe to <item_type> <item_id>"""
        assert(item_type in self.supported_follow_types)
        assert(item_id == str(item_id))

        try:
            return self._followers[item_type][item_id]
        except KeyError:
            return ()

    # like API

    def like(self, item_type, user_id, item_id):
        """User <user_id> likes <item_type> <item_id>"""
        assert(item_type in self.supported_like_types)
        assert(user_id == str(user_id))
        assert(item_id == str(item_id))

        self._likes[item_type].insert(user_id, OOBTree.OOTreeSet())
        self._liked[item_type].insert(item_id, OOBTree.OOTreeSet())

        self._likes[item_type][user_id].insert(item_id)
        self._liked[item_type][item_id].insert(user_id)

    def unlike(self, item_type, user_id, item_id):
        """User <user_id> unlikes <item_type> <item_id>"""
        assert(item_type in self.supported_like_types)
        assert(user_id == str(user_id))
        assert(item_id == str(item_id))

        try:
            self._likes[item_type][user_id].remove(item_id)
        except KeyError:
            pass
        try:
            self._liked[item_type][item_id].remove(user_id)
        except KeyError:
            pass

    def get_likes(self, item_type, user_id):
        """List all <item_type> liked by <user_id>"""
        assert(user_id == str(user_id))
        try:
            return self._likes[item_type][user_id]
        except KeyError:
            return []

    def get_likers(self, item_type, item_id):
        """List all userids liking <item_type> <item_id>"""
        assert(item_id == str(item_id))
        try:
            return self._liked[item_type][item_id]
        except KeyError:
            return []

    def is_liked(self, item_type, user_id, item_id):
        """Does <user_id> like <item_type> <item_id>?"""
        assert(user_id == str(user_id))
        assert(item_id == str(item_id))

        try:
            return user_id in self.get_likers(item_type, item_id)
        except KeyError:
            return False

    # tags API

    def tag(self, item_type, user_id, item_id, *tags):
        """User <user_id> adds tags <*tags> on <item_type> <item_id>"""
        assert(item_type in self.supported_tag_types)
        assert(user_id == str(user_id))
        assert(item_id == str(item_id))
        assert([tag == str(tag) for tag in tags])

        for tag in tags:

            if user_id not in self._tagged:
                self._tagged[user_id] = OOBTree.OOBTree()
            if tag not in self._tagged[user_id]:
                self._tagged[user_id][tag] = OOBTree.OOBTree()
                for _type in self.supported_tag_types:
                    self._tagged[user_id][tag][_type] = OOBTree.OOTreeSet()
            self._tagged[user_id][tag][item_type].insert(item_id)

            if item_id not in self._tagger[item_type]:
                self._tagger[item_type][item_id] = OOBTree.OOBTree()
            if tag not in self._tagger[item_type][item_id]:
                self._tagger[item_type][item_id][tag] = OOBTree.OOTreeSet()
            self._tagger[item_type][item_id][tag].insert(user_id)

            if user_id not in self._tags:
                self._tags[user_id] = OOBTree.OOBTree()
                for _type in self.supported_tag_types:
                    self._tags[user_id][_type] = OOBTree.OOBTree()
            if item_id not in self._tags[user_id][item_type]:
                self._tags[user_id][item_type][item_id] = OOBTree.OOTreeSet()
            self._tags[user_id][item_type][item_id].insert(tag)

            if tag not in self._all:
                self._all[tag] = OOBTree.OOBTree()
                for _type in self.supported_tag_types:
                    self._all[tag][_type] = OOBTree.OOBTree()
                if item_id not in self._all[tag][item_type]:
                    self._all[tag][item_type][item_id] = OOBTree.OOTreeSet()
            self._all[tag][item_type][item_id].insert(user_id)

    def untag(self, item_type, user_id, item_id, *tags):
        """User <user_id> removes tags <*tags> from <item_type> <item_id>"""
        assert(item_type in self.supported_tag_types)
        assert(user_id == str(user_id))
        assert(item_id == str(item_id))
        assert([tag == str(tag) for tag in tags])
        for tag in tags:
            self._tagged[user_id][tag][item_type].remove(item_id)
            self._tagger[item_type][item_id][tag].remove(user_id)
            self._all[tag][item_type][item_id].remove(user_id)

    def get_tagged(self, item_type=None, userid=None, tag=None):
        """
        List <item_type> item_ids tagged as <tag> by <user_id>.
        If item_type==None: returns {item_type: (objectids..)} mapping
        if userid==None: returns {tag: {item_type: (objectids..)}} mapping
        If tag==None: returns {tag: {item_type: (objectids..)}} mapping
        """

    def get_taggers(self, item_type, item_id, tag=None):
        """
        List user_ids that tagged <item_type> <item_id> with <tag>.
        If tag==None: returns {tag: (itemids..)} mapping
        """

    def get_tags(self, item_type, item_id, user_id=None):
        """
        List tags set on <item_type> <item_id> by <user_id>.
        If user_id==None: return {tag: (userids..)} mapping
        """
        return self._tags[user_id][item_type][item_id]

    def is_tagged(self, item_type, user_id, item_id, tag):
        """Did <user_id> apply tag <tag> on <item_type> <item_id>?"""
