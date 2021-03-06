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
		self.support = None
		self.damagetaken = 0
		self.attackchains = {}

		# sums for database
		self.win = 0
		self.loss = 0
		self.tie = 0
		
		self.attacks = 0
		self.heals = 0
		self.greens = 0
		self.phases = 0
		self.jaunts = 0

		self.attacktiming = []
		self.healtiming = []
		self.phasetiming = []
		self.jaunttiming = []
		self.firstattacks = 0 # when first atk on spike
		self.alphaheals   = 0 # when first heal on spike

		self.sets = set()
		self.set1 = None
		self.set2 = None
		self.archetype = None

		# parse variables, updated for calculating other attribs
		self.poscurrent = None
		self.posdelay = None
		self.posrecent = []
		self.lastdeath = -30000 # at least -config['death_cooldown']
		self.lastphase = None
		self.lasthp = 0
		self.firstherofound = False
		self.possible_ats = {"arachnos_soldier","arachnos_widow","blaster","melee","controller","defender/corruptor","dominator","mastermind","peacebringer","sentinel","warshade"}


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
		self.aid = aid # actionid, primary key element
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
		self.reverse = False

		# addl action parsing
		self.hithp = None # hit hp of TARGET
		self.casthp = None # cast hp of TARGET, for fat fingers

		# spike data
		self.spikeid = None
		self.spiketime = None # time relative to spike start
		self.spikehittime = None # time relative to spike start
		self.spikeherocount = None # action number on spike, by player

		# action attributes, from powers json
		self.tags = set()
		self.type = None
		self.target_type = None
		self.effect_area = None
		self.icon = None



class Spike:
	def __init__(self, spikeid):
		self.sid = spikeid
		self.tid = None
		self.target = None
		self.targetteam = None

		# calculated
		self.start = None
		self.startdelta = 0
		self.end = None
		self.duration = None
		self.kill = None
		self.reset = False
		self.hploss = 0
		self.hitwindow = None

		self.nattacks = 0
		self.nattackers = 0
		self.nheals = 0
		self.ngreens = 0

class Hitpoints:
	def __init__(self, hid, time, hp, hploss):
		self.hid = hid
		self.time = time
		self.hp = hp
		self.hploss = hploss