# -*- coding:utf-8 -*-

from gdata.youtube.client import YouTubeClient

class CollectYouTube(object):
	def __init__(self, email = None, password = None):
		self.__client = YouTubeClient()
		if email and password:
			self.ssl = True
			self.__client.client_login(
				email, password, u'MyVideoCollection'
			)

	def _ismatch(self, categories, word):
		for c in categories:
			if c.term == word: return True
		return False

	def _get_attribute_value(self, elem, attrname):
		attrs = elem.GetAttributes(attrname)
		if len(attrs)==1:
			return attrs[0].value
		return None

	def _makelinkdata(self, entry):
		ret = {u'title': entry.title.text, u'url': entry.GetHtmlLink().href}
		for group in entry.GetElements(u'group'):
			for description in group.GetElements(u'description'):
				ret[u'description'] = description.text
			for videoid in group.GetElements(u'videoid'):
				ret[u'videoid'] = videoid.text
#			for statistics in group.getElements(u'statistics'):
#				ret[u'views'] = self._get_attribute_value(statistics, u'viewCount')
			# 次にサムネイル関連
			for thumb in group.GetElements(u'thumbnail'):
				n = self._get_attribute_value(thumb, u'name')
				if n == u'default':
					ret[u'thumbnail'] = self._get_attribute_value(thumb, u'url')
					ret[u'width'] = self._get_attribute_value(thumb, u'width')
					ret[u'height'] = self._get_attribute_value(thumb, u'height')
				elif n == u'hqdefault':
					ret[u'hqthumbnail'] = self._get_attribute_value(thumb, u'url')
					ret[u'hqwidth'] = self._get_attribute_value(thumb, u'width')
					ret[u'hqheight'] = self._get_attribute_value(thumb, u'height')
				elif n == u'start':
					ret[u'thumbnail1'] = self._get_attribute_value(thumb, u'url')
				elif n == u'middle':
					ret[u'thumbnail2'] = self._get_attribute_value(thumb, u'url')
				elif n == u'end':
					ret[u'thumbnail3'] = self._get_attribute_value(thumb, u'url')
		return ret

	def collect(self, username, word):
		ret = []
		try:
			feed = self.__client.GetUserFeed(username=username)
			while feed:
				for entry in feed.entry:
					if self._ismatch(entry.category, word):
						ret.append(self._makelinkdata(entry))
				if feed.GetNextLink():
					feed = self.__client.GetNext(feed)
				else:
					feed = None
		except: pass
		return ret


