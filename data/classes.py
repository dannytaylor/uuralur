import json
playernames = json.loads(open('data/player_names.json').read())

class Hero:
	def __init__(self, hid, name):
		# constants (or final calculated)
		self.hid = hid # hero id (defined by demo entity ID)
		self.name = name
		self.playername = None
		self.team = None
		self.hpmax = 0

		# calculated
		self.deaths = 0
		self.targets = 0
		self.support = 0
		self.damagetaken = 0

		self.sets = set()
		self.set1 = None
		self.set2 = None
		self.archetype = None

		# parse variables (varying, but not added to database)
		self.poscurrent = None
		self.posdelay = None
		self.posrecent = []
		self.lastdeath = 0
		self.lastphase = None
		self.lasthp = 0
		self.firstherofound = False


	def setplayername(override=None):
		if override['names']:
			for oldname in override['names']:
				p.name = override['names']['override']
		for playername,characters in playernames.items():
			for c in characters:
				if c == name:
					self.playername = playername

class Action:
	def __init__(self, aid, hid, action, time_ms):
		self.aid = aid # actionid
		self.action = action
		self.hid = hid
		self.tid = None
		self.target = None
		self.time_ms = time_ms
		self.team = None
		self.deaths = 0
		self.dist = None
		self.hittime = None
		self.roottime = None # time spend in cast
		self.spikeid = None
		self.reverse = False

		self.tags = []
		self.attribs = []


class Spike:
	def __init__(self, spikeid):
		self.sid = spikeid
		self.tid = None
		self.tname = None
		self.start = None
		self.end = None
		self.duration = None
		self.time = None
		self.kill = 0
		self.reset = False