# -*- coding:utf-8 -*-
import cgi, os, mimetypes, urllib, datetime, time

import video

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app, login_required
from google.appengine.ext.webapp import template
from google.appengine.ext import db

from appengine_utilities.sessions import Session

class VideoCollection(db.Model):
	owner = db.UserProperty(auto_current_user=True)
	keyword = db.StringProperty()
	yt_id = db.StringProperty()
	yt_name = db.StringProperty()
	yt_pswd = db.StringProperty()
	pswd = db.StringProperty()
	fetch_count = db.IntegerProperty()
	home_url = db.LinkProperty()
	
	@staticmethod
	def get_collection(user):
		q = VideoCollection.gql(u'WHERE owner = :1', user)
		if q.count() == 1:
			return q.get()
		for col in q:
			col.delete()
		return None

	@staticmethod
	def get_by_keyword(keywd, pswd):
		q = VideoCollection.gql(u'WHERE keyword = :1 AND pswd = :2', keywd, pswd)
		if q.count() == 1:
			return q.get()
		return None

	def gamelists(self):
		return GameList.gql(u'WHERE coll = :1 ORDER BY description DESC', self.key())

class GameList(db.Model):
	coll = db.ReferenceProperty(VideoCollection)
	description = db.StringProperty()

	def games(self):
		return Game.gql(u'WHERE games = :1 ORDER BY title', self.key())

	@staticmethod
	def get_by_description(descr, vc):
		q = GameList.gql(u'WHERE description = :1', descr)
		if q.count() == 1:
			return q.get()
		else:
			ret = GameList()
			ret.description = descr
			ret.coll = vc
			ret.put()
			return ret

class Game(db.Model):
	games = db.ReferenceProperty(GameList)
	title = db.StringProperty()
	thumbnail = db.LinkProperty()
	width = db.IntegerProperty()
	height = db.IntegerProperty()

	def has_next(self):
		return self.next() is not None

	def has_prev(self):
		return self.prev() is not None

	def next(self):
		found = False
		for g in Game.gql(u'WHERE games = :1 ORDER BY title', self.games.key()):
			if found: return g
			if g.title == self.title:
				found = True
		return None

	def prev(self):
		found = None
		for g in Game.gql(u'WHERE games = :1 ORDER BY title', self.games.key()):
			if g.title == self.title:
				return found
			found = g
		return None

	def entries(self):
		return VideoEntry.gql(u'WHERE game = :1 ORDER BY number', self.key())

	def thumbs(self):
		ret = []
		for e in self.entries():
			for t in e.thumbs():
				ret.append(t)
		return ret

	@staticmethod
	def get_by_title(games, title, entry):
		num = None
		if title.endswith(u'Q'):
			x, y = title.rsplit(u' ', 1)
			num = int(y[:-1])
			title = x
		q = Game.gql(u'WHERE title = :1 AND games = :2', title, games)
		if q.count() == 1:
			return q.get(), num
		else:
			ret = Game()
			ret.games = games
			ret.title = title
		ret.thumbnail = entry[u'thumbnail']
		ret.width = int(entry[u'width'])
		ret.height = int(entry[u'height'])
		ret.put()
		return ret, num

class VideoEntry(db.Model):
	game = db.ReferenceProperty(Game)
	videoid = db.StringProperty()
	number = db.IntegerProperty()
	url = db.LinkProperty()
	thumbnail = db.LinkProperty()
	thumbnail1 = db.LinkProperty()
	thumbnail2 = db.LinkProperty()
	thumbnail3 = db.LinkProperty()
	width = db.IntegerProperty()
	height = db.IntegerProperty()
	hqthumbnail = db.LinkProperty()
	hqwidth = db.IntegerProperty()
	hqheight = db.IntegerProperty()

	@staticmethod
	def has_entry(videoid):
		q = VideoEntry.gql(u'WHERE videoid = :1', videoid)
		return q.count() == 1

	def embed(self):
		return u'http://www.youtube.com/embed/' + self.videoid

	def thumbs(self):
		return [self.thumbnail1, self.thumbnail2, self.thumbnail3]


class VideoList(webapp.RequestHandler):
	def __show_list(self):
		if self.sess.has_key(u'vc'):
			vc = VideoCollection.get(self.sess[u'vc'])
			pos = int(self.request.get(u'pos', u'0'))
			q = vc.gamelists()
			if pos < vc.fetch_count:
				prev = None
				has_prev = False
			else:
				has_prev = True
			prev = pos - vc.fetch_count
			if pos + vc.fetch_count < q.count():
				next = pos + vc.fetch_count
			else:
				next = None
			template_values = {
				u'title'	: vc.keyword + u'試合内容',
				u'pageid'	: unicode(vc.key())+unicode(pos),
				u'has_prev'	: has_prev,
				u'prev'		: prev,
				u'next'		: next,
				u'home'		: vc.keyword,
				u'home_url'	: vc.home_url,
				u'gamelists': q.fetch(offset=pos, limit=vc.fetch_count)
			}
			path = os.path.join(os.path.dirname(__file__), 'index.html')
			self.response.out.write(template.render(path, template_values))
		else:
			path = os.path.join(os.path.dirname(__file__), 'login.html')
			self.response.out.write(template.render(path, {
				u'title'	: u'ログイン',
				u'home'		: u'トップ画面へ',
				u'home_url'	: u'/',
				u'pageid'	: u'loginscreen'
			}))
		
	def get(self):
		self.sess = Session()
		self.__show_list()

	def post(self):
		self.sess = Session()
		vc = VideoCollection.get_by_keyword(
			self.request.get(u'keyword'), self.request.get(u'pswd'))
		if vc:
			self.sess[u'vc'] = vc.key()
			time.sleep(1)
		self.__show_list()

class GameView(webapp.RequestHandler):
	def get(self):
		game = Game.get(self.request.get(u'game'))
		self.sess = Session()
		if self.sess.has_key(u'vc') and self.sess[u'vc'] == game.games.coll.key():
			path = os.path.join(os.path.dirname(__file__), 'game.html')
			self.response.out.write(template.render(path, {
				u'title'	: game.title,
				u'home'		: game.games.coll.keyword,
				u'home_url'	: game.games.coll.home_url,
				u'pageid'	: game.key(),
				u'game':	game
			}))
		else:
			del self.sess[u'vc']
			self.redirect(u'/')

class Config(webapp.RequestHandler):
	def __show_config(self, vc):
		path = os.path.join(os.path.dirname(__file__), u'config.html')
		if vc is None:
			gl = []
		else:
			gl = vc.gamelists()
		self.response.out.write(template.render(path, {
			u'title'	: u'Youtube収集設定',
			u'home'		: u'トップ画面へ',
			u'home_url'	: u'/',
			u'pageid'	: u'ytcollectpage',
			u'gamelists': gl,
			u'vc'		: vc or VideoCollection()
		}))
		
	@login_required
	def get(self):
		self.__show_config(VideoCollection.get_collection(users.get_current_user()))
	
	def post(self):
		vc = VideoCollection.get_collection(users.get_current_user()) or VideoCollection()
		vc.keyword = self.request.get(u'keyword')
		vc.yt_id = self.request.get(u'yt_id')
		vc.yt_name = self.request.get(u'yt_name')
		vc.yt_pswd = self.request.get(u'yt_pswd')
		vc.pswd = self.request.get(u'pswd')
		vc.fetch_count = int(self.request.get(u'count'))
		vc.home_url = self.request.get(u'home_url')
		vc.put()
		self.__show_config(vc)
		
class Api(webapp.RequestHandler):
	@login_required
	def get(self):
		vc = VideoCollection.get_collection(users.get_current_user())
		if vc is None:
			self.response.set_status(500)
		m = self.request.get(u'method')
		if m == u'clear':
			for gl in vc.gamelists():
				for g in gl.games():
					for ve in g.entries():
						ve.delete()
					g.delete()
				gl.delete()
			self.response.set_status(200)
		if m == u'create':
			gl = GameList()
			gl.coll = vc;
			gl.description = self.request.get(u'name').strip(u'"')
			gl.put()
			self.response.set_status(200)
		elif m == u'scan':
			yt = video.CollectYouTube(vc.yt_id, vc.yt_pswd)
			for entry in yt.collect(vc.yt_name, vc.keyword):
				if VideoEntry.has_entry(entry[u'videoid']):
					# 既にアップロード済
					continue
				games = GameList.get_by_description(entry[u'description'], vc)
				game, num = Game.get_by_title(games, entry[u'title'], entry)
				ve = VideoEntry()
				ve.game = game
				ve.videoid = entry[u'videoid']
				ve.number = num
				ve.url = entry[u'url']
				ve.thumbnail = entry[u'thumbnail']
				ve.thumbnail1 = entry[u'thumbnail1']
				ve.thumbnail2 = entry[u'thumbnail2']
				ve.thumbnail3 = entry[u'thumbnail3']
				ve.width = int(entry[u'width'])
				ve.height = int(entry[u'height'])
				ve.hqthumbnail = entry[u'hqthumbnail']
				ve.hqwidth = int(entry[u'hqwidth'])
				ve.hqheight = int(entry[u'hqheight'])
				ve.put()
			self.response.set_status(200)
	def post(self):
		gm = None
		for i in range(1, 10):
			ve = VideoEntry()
			ve.videoid = self.request.get(u'game' + unicode(i))
			if len(ve.videoid)==0: break
			ve.number = i
			ve.url = u'https://www.youtube.com/watch?v='+ve.videoid+'&feature=youtube_gdata'
			ve.height = 90
			ve.width = 120
			ve.hqheight = 360
			ve.hqwidth = 480
			ve.thumbnail = u'http://i.ytimg.com/vi/'+ve.videoid+'/default.jpg'
			ve.thumbnail1 = u'http://i.ytimg.com/vi/'+ve.videoid+'/1.jpg'
			ve.thumbnail2 = u'http://i.ytimg.com/vi/'+ve.videoid+'/2.jpg'
			ve.thumbnail3 = u'http://i.ytimg.com/vi/'+ve.videoid+'/3.jpg'
			ve.hqthumbnail = u'http://i.ytimg.com/vi/'+ve.videoid+'/hqdefault.jpg'
			if gm is None:
				gm = Game()
				gm.games = GameList.get(self.request.get(u'gamelist'))
				gm.title = self.request.get(u'gamename')
				gm.thumbnail = ve.thumbnail
				gm.width = ve.width
				gm.height = ve.height
				gm.put()
			ve.game = gm
			ve.put()
		self.redirect(u'/config')
			
				
application = webapp.WSGIApplication(
	[
	('/', VideoList),
	('/list', VideoList),
	('/game', GameView),
	('/config', Config),
	('/api', Api),
	], debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
