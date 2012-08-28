__version_info__ = (0,0,1)
__version__ = '0.0.1'

import requests
import json
import urllib
import httplib

api_uri = 'http://api.discogs.com'
user_agent = None


class DiscogsAPIError(Exception):
	"""Root Exception class for Discogs API errors."""
	pass


class UserAgentError(DiscogsAPIError):
	"""Exception class for User-Agent problems."""
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return repr(self.msg)

class HTTPError(DiscogsAPIError):
	"""Exception class for HTTP(lib) errors."""
	def __init__(self, code):
		self.code = code
		self.msg = httplib.responses[self.code]

	def __str__(self):
		return "HTTP status %i: %s." % (self.code, self.msg)


class APIBase(object):
	def __init__(self):
		self._cached_response = None
		self._params = {}
		self._check_user_agent()            

	def __str__(self):
		return '<%s, id: %s>' % (self.__class__.__name__, self._id)

	def __repr__(self):
		return self.__str__().encode('utf-8')

	def _check_user_agent(self):
		self._headers = {'accept-encoding': 'gzip, deflate', 'user-agent': user_agent}
		if self._headers['user-agent'] is None:
			raise UserAgentError("Invalid or no User-Agent set.")

	def _clear_cache(self):
		self._cached_response = None

	@property
	def _response(self):
		if not self._cached_response:
			self._cached_response = requests.get(self._uri, params=self._params, headers=self._headers)
		return self._cached_response

	@property
	def _uri(self):
		return '%s/%s' % (api_uri, self._path)#, urllib.quote_plus(unicode(self._id).encode('utf-8')))

	@property
	def data(self):
		if self._response.content and self._response.status_code == 200:
			release_json = json.loads(self._response.content)
			return release_json
		else:
			status_code = self._response.status_code
			raise HTTPError(status_code)

class Search(APIBase):

	def _class_from_string(self, type):
		return {'artist': Artist, 'release': Release}[type]

	def __init__(self, query):
		APIBase.__init__(self)
		self._path = 'database/search'
		self._params = {'q': query}

	def results(self, type=None, page=None):
		if type:
			self._params['type'] = type
		if page:
			self._params['page'] = page

		results = []

		for result in self.data['results']:
			results.append(self._class_from_string(result['type'])(result))

		return results

class Artist(APIBase):
	def __init__(self, data):
		self._name = None
		self._thumb = None
		self._profile = None
		self._image = None
		self._releases, self._masters = [], []
		if isinstance(data, int):
			self._id = data
		else:
			self._id = data['id']
			self._name = data['title'] if 'title' in data.keys() else None
			self._thumb = data['thumb'] if 'thumb' in data.keys() else None
		self._reset_path()
		APIBase.__init__(self)

	def _reset_path(self):
		self._path = 'artists/%s' % self._id

	@property
	def name(self):
		if not self._name:
			self._name = self.data.get('name')
		return self._name

	@property
	def profile(self):
		if not self._profile:
			self._profile = self.data.get('profile')
		return self._profile

	@property
	def image(self):
		if not self._image:
			self._image = self.data.get('images')[0]['uri150']
		return self._image

	@property
	def thumb(self):
		return self._thumb

	@property
	def releases(self):
		if not self._releases:
			self._path = '/artists/%s/releases' % self._id
			self._clear_cache()
			for r in self.data.get('releases'):
				self._releases.append(Release(r))
			self._reset_path()
			self._clear_cache()
		return self._releases

	@property
	def masters(self):
		if not self._masters:
			for r in self.releases:
				if r.type == 'master':
					self._masters.append(r)
		return self._masters

class Release(APIBase):
	def __init__(self, data):
		self._title = None
		self._thumb = None
		self._released = None
		self._master = None
		self._type = None
		if isinstance(data, int):
			self._id = data
		else:
			self._id = data['id']
			self._type = data.get('type')
			self._title = data.get('title')
			self._thumb = data.get('thumb')
			self._year = data.get('year')
	
		self._path = 'releases/%s' % self._id
		APIBase.__init__(self)

	@property
	def title(self):
		if not self._title:
			self._title = self.data.get('title')
		return self._title

	@property
	def year(self):
		if not self._year:
			self._year = self.data.get('year')
		return self._year

	@property
	def type(self):
		if not self._type:
			self._type = self.data.get('type')
		return self._type

	@property
	def released(self):
		if not self._released:
			self._released = self.data.get('released')
		return self._released

	@property
	def master(self):
		if not self._master:
			master_id = self.data.get('master_id')
			self._master =	Master(master_id) if master_id else None
		return self._master

class Master(APIBase):
	def __init__(self, id):
		self._id = id
		self._released = None
		self._title = None
		self._path = 'masters/%s' % self._id
		APIBase.__init__(self)

	@property
	def title(self):
		if not self._title:
			self._title = self.data.get('title')
		return self._title

	@property
	def released(self):
		if not self._released:
			self._released = self.data.get('released')
		return self._released	

class User(APIBase):
	def __init__(self, username):
		self._username = username
		self._reset_path()
		self._collection = []
		APIBase.__init__(self)

	def _reset_path(self):
		self._path = 'users/%s' % self._username

	def collection(self, sort=None, order=None, page=None):
		self._path = '/users/%s/collection/folders/0/releases' % self._username
		self._clear_cache()
		self._params = {'sort': sort, 'sort_order': order, 'page': page}
		collection = []
		for r in self.data.get('releases'):
			collection.append(Release(r.get('basic_information')))
		self._reset_path()
		self._clear_cache()
		return collection