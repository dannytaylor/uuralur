#!/usr/bin/env python

import os, sys, time, math, argparse, datetime,statistics

import yaml, json, re
import numpy as np

# parse data structures
import data.data as d
import data.classes as c
import database as db
# import data.override as override

# load config settings and database
config = yaml.safe_load(open('data/config.yaml'))
powers = json.loads(open('data/powers.json').read())
fx     = json.loads(open('data/fx.json').read())
playernames = json.loads(open('data/player_names.json').read())

HERODUMP = True
OVERRIDE = False

hero_data = {}
herodump = {}
overrides = {}
if os.path.exists('data/hero_data.json'):
	hero_data = json.loads(open('data/hero_data.json').read())
if os.path.exists('data/overrides.json'):
	overrides = json.loads(open('data/overrides.json').read())

# converts demo file to list
def demo2lines(demo):
	line = [p.replace('\n','').replace('\"','') for p in re.split("( |\\\".*?\\\"|'.*?')", demo.readline()) if p.strip()] # from https://stackoverflow.com/questions/79968/split-a-string-by-spaces-preserving-quoted-substrings-in-python
	lines = [line]
	demomap = None
	while line:
		line = [p.replace('\n','').replace('\"','') for p in re.split("( |\\\".*?\\\"|'.*?')", demo.readline()) if p.strip()]
		if len(line) > 2:
			if line[0] != '0' or line[2] not in d.ignore_line_ent:
				newline = []
				for l in line:
					if not isinstance(l, str): newline.append(l)
					elif not l.isnumeric(): newline.append(l)
					elif '.' in l: newline.append(float(l))
					else: newline.append(int(l))
				lines.append(newline)
			if line[2] == 'Map':
				demomap = line[3]
				if demomap in d.mapaliases: demomap = d.mapaliases[demomap]
	return lines,demomap

# returns player names and ids from demo
def demo2heroes(lines):
	heroes = {}
	npcs = []
	for i in range(min(30000,len(lines))): # should find all heroes by 30k lines
		if lines[i][2] == "NPC" and lines[i][3] not in d.ignorecostumes:
			npcs.append(lines[i][1])
		if lines[i][2] == "NEW" and lines[i][1] not in npcs:
			name = str(lines[i][3])
			hid = lines[i][1]
			if name not in d.namefilter and name not in heroes and i < len(lines) - 6:
				isnpc = False
				for j in range(8): # check next 5 lines for NPC tag
					if lines[i+j][1] == hid and (lines[i+j][2] == 'NPC' or lines[i+j][2] == 'EntTypeFile'):
						isnpc = True
				if not isnpc and hid not in heroes:
					heroes[hid] = c.Hero(hid,name)
					if len(heroes) == 1:
						heroes[hid].firstherofound = True # for team ordering later
		if len(heroes) >= 16:
			break

	# assign player names to hero names
	for hid,h in heroes.items():
		for pname,hnames in playernames.items():
			for hname in hnames:
				if h.name.lower() == hname.lower():
					h.playername = pname
					break
	return heroes

# checks if 3 players are all separate from each other
def posseparation(points):
	for pid,p in points.items():
		for tid,t in points.items():
			if pid != tid:
				dist = np.linalg.norm(p - t)
				if dist < config['pos_start_distance']:
					return False
	return True

# returns match start time/end of buff timer
def matchstart(lines,h):
	time_ms = 0
	starttime = 0
	pos = {}
	for i in range(len(lines)):
		time_ms += int(lines[i][0])
		hid = lines[i][1]
		# determine start time by first jump anim
		if lines[i][2] == 'MOV' and 'JUMP' in lines[i][3] and hid in h:
			return time_ms
		# if (3) random heroes are separated from each other start match
		elif lines[i][2] == 'POS' and lines[i][5] and hid in h:
			if hid in pos or len(pos) < 3:
				pos[hid] = np.array([float(lines[i][3]),float(lines[i][4]),float(lines[i][5])])
			if len(pos) == 3:
				if posseparation(pos):
					return time_ms

def countdeath(h,time_ms):
	if time_ms > config['death_cooldown'] + h.lastdeath: # at least 5 sec from last death to prevent double counts
		h.deaths += 1
		h.lastdeath = time_ms
		return True
	else:
		return False

def updateactionattribs(a):
	a.tags = set(powers[a.action]['tags'])
	a.type = powers[a.action]['type']
	a.target_type = powers[a.action]['target_type']
	a.effect_area = powers[a.action]['effect_area']
	a.icon = powers[a.action]['icon']
	if a.type == "Toggle" and a.target_type == "Self" and "Phase" in a.tags: # manual override phases for sql filtering
		a.type = "Phase"
	if "Delay" in powers[a.action]['tags']:
		a.time_ms -= (powers[a.action]['frames_before_hit'])
	a.hittime = a.time_ms + powers[a.action]['frames_before_hit']
	if a.tid and a.dist:
		a.hittime += int(1000*a.dist/powers[a.action]['projectile_speed'])
	a.roottime = a.time_ms + powers[a.action]['frames_attack']

# determine at by process of elimination from powers
def determinearchetypes(heroes,actions):
	for hid,h in heroes.items():
		possible_ats = h.possible_ats.copy()
		for a in actions: # loop until end or 2 powersets determined
			if hid == a.hid and a.action in powers and len(powers[a.action]['archetypes'])>0:
				possible_ats = possible_ats.intersection(set(powers[a.action]['archetypes']))

			# found a demo with a controller with >1606 - manually corrected it, but could be a reoccuring error
			for maxhp,ats in d.at_maxhp.items():
				if h.hpmax > maxhp:
					possible_ats.difference_update(ats)

			if len(possible_ats) == 1:
				h.archetype = max(possible_ats)
				# log a determined AT if found and not from a previous demo
				if h.name in hero_data:
					if "archetype" not in hero_data[h.name]:
						hero_data[h.name]['archetype'] = h.archetype
				elif HERODUMP: # if not in hero data
					herodump[h.name] = {'archetype':h.archetype}
				break

		h.possible_ats = possible_ats
		# if no AT determined look if it was found in another demo
		if not h.archetype:
			if h.name in hero_data and 'archetype' in hero_data[h.name]:
				h.archetype = hero_data[h.name]['archetype']
				h.possible_ats.add(h.archetype)

# fetch predetermined sets if AT + 1 set determined
def fetchpowersets(heroes):
	for hid,h in heroes.items():
		if HERODUMP and h.name not in herodump and h.name not in hero_data: # add name for undefined dumping
			herodump[h.name] = {}
		if h.archetype and h.sets:
			if len(h.sets) == 1 and h.name in hero_data and 'sets' in hero_data[h.name]: # if only 1 set determined by 2 sets logged
				h.sets = hero_data[h.name]['sets']
			elif HERODUMP and len(h.sets) == 2: # only dump sets if both are determined
				if h.name not in hero_data and 'sets' not in herodump[h.name]: # only dump psets if archetype is determined
					herodump[h.name]['sets'] = list(h.sets)


# order the powers sets based on arch
def orderpowersets(heroes):
	for hid,h in heroes.items():

		# assume if healer with no secondary power use it's a defender
		# pretty safe assumption mostly
		if not h.archetype and len(h.sets) == 1 and max(h.sets) in d.heal_sets:
			h.archetype = "defender/corruptor"

		hset = [None,None]
		if h.archetype and h.sets:
			primaries 	= powers['powercategories'][h.archetype]['primary_category']
			secondaries = powers['powercategories'][h.archetype]['secondary_category']
			for s in h.sets:
				if s in primaries:
					hset[0] = s
				elif s in secondaries:
					hset[1] = s
		else:
			hset = list(h.sets)
			if len(hset) == 1:
				hset.insert(0,None)
		h.sets = hset


# determine powersets from determined AT and by process of elimination from powers
def determinepowersets(heroes,actions):
	determinearchetypes(heroes,actions)
	for hid,h in heroes.items():
		for a in actions: # loop until end or 2 powersets determined
			if (hid == a.hid and len(h.sets) < 2 and a.action in powers): # if valid action by hid
				if (
					('Pool' not in powers[a.action]['tags'] and 'Temporary_Powers' not in powers[a.action]['tags'] and 'Inspirations' not in powers[a.action]['tags'])
					and ('Epic' not in powers[a.action]['tags'] or 'AllowEpic' in powers[a.action]['tags'])# only allow certain epic powers to be used for pset determination
					):
					psets = powers[a.action]['powersets'] # possible power sets for action
					# check valid powersets for calculated h.possible_ats
					possible_psets = set()
					for ps in psets: #
						ps_ats = set(powers['powersets'][ps]) # ATs that can use pset
						if len(ps_ats.intersection(h.possible_ats)) > 0: # does the pset AT have anything in common with the determined ATs?
							possible_psets.add(ps) # if true then the pset is valid

					psets = [ps for ps in psets if ps in possible_psets] # remove non-valid powersets
					
					if h.archetype:
						psets = list(set(psets).intersection(powers['archetypes'][h.archetype]))
					if (len(psets) == 1 and psets[0] not in h.sets): # ignore epic/pool/temp/insps
						h.sets.add(psets[0])

			if len(h.sets) == 2:
				break

	fetchpowersets(heroes)

	
	# sort sets in correct order for the archetype
	orderpowersets(heroes)

	# allow writing to db for no sets
	for hid,h in heroes.items():
		if not h.sets:
			h.sets = [None,None]

# handle hold actions waiting to be determined
def parseholdactions(actions,holdactions):
	for a in actions:
		if isinstance(a.action,list): # for every actions with undefined power'
			for ha in holdactions:
				# if action matches a hold action within the time window
				if {a.hid,a.tid} == {ha.hid,ha.tid}:
					if (a.time_ms > ha.time_ms - config['hold_window'] and a.time_ms < ha.time_ms + config['hold_window']):
						a.action = ha.action
					break
			# if no corresponding holdaction is found default to first in actionname list
			if isinstance(a.action,list): 
				a.action = a.action[0]
			if a.tid and a.dist:
				a.hittime = a.time_ms + powers[a.action]['frames_before_hit'] + int(1000*(a.dist/powers[a.action]['projectile_speed']))
			else:
				a.hittime = a.time_ms + powers[a.action]['frames_before_hit']
		if "MOV" not in a.tags:
			updateactionattribs(a)
		elif "MOV" in a.tags:
			a.icon = d.movicons[a.action]

	# remove all actions with undefined powers (.action is a list)
	actions = [a for a in actions if not isinstance(a.action,list)]

# checks for a target on the next 5 lines 
def checktarget(hid,lines,h,i,a,reverse):
	rangecheck = min(len(lines)-i-1,5) # catches errors for target finding at end of demo
	for j in range(1,rangecheck): # check for target
		if (
			(lines[i+j][1] == hid and lines[i+j][2] == 'TARGET' and lines[i+j][3] == 'ENT' and lines[i+j][1] != lines[i+j][4])
			or (lines[i+j][1] == hid and lines[i+j][2] == 'PREVTARGET' and lines[i+j][3] == 'ENT' and lines[i+j][1] != lines[i+j][4])
			):
			tidtmp = lines[i+j][4]
			if tidtmp in h and tidtmp != hid:
				a.tid = tidtmp
				if reverse:
					a.tid = a.hid
					a.hid = tidtmp
				try:
					a.dist = np.linalg.norm(h[a.hid].poscurrent - h[a.tid].posdelay)
				except:
					a.dist = None # if player has no distance entity yet in demo
				return a
		elif lines[i+j][1] == hid and lines[i+j][2] == 'FX':
			return a
	return a

# assigns most recent HP value when a power is calculated to hit
def hponaction(hitpoints,actions):
	for a in actions:
		# cast hp of target
		if a.tid:
			casthp = None
			for hp in hitpoints:
				if hp.hid == a.tid and hp.time <= a.time_ms:
					casthp = hp.hp
				elif hp.hid == a.tid and hp.time > a.time_ms:
					break
			a.casthp = casthp
		# hit hp
		if a.hittime:
			hithp = None
			if a.tid:
				for hp in hitpoints:
					if hp.hid == a.tid and hp.time <= a.hittime:
						hithp = hp.hp
					elif hp.hid == a.tid and hp.time > a.hittime:
						break
			elif not a.tid and a.target_type == 'Self':
				for hp in hitpoints:
					if hp.hid == a.hid and hp.time <= a.hittime:
						hithp = hp.hp
					elif hp.hid == a.hid and hp.time > a.hittime:
						break
			a.hithp = hithp
	return

# tag actions with "Phase Hit" if target phases
def phasehits(actions):
	phases = [] # [hid,hittime]
	for a in actions:
		if "Phase" in a.tags:
			phases.append([a.hid,a.time_ms])
	for a in actions:
		phasecheck = [p for p in phases if (a.tid == p[0] and a.time_ms > p[1]+ config['phase_hit_delay'] and a.time_ms < p[1] + config['phase_hit_reset'])]
		if phasecheck: a.tags.add("Phase Hit")

# remove repeat actions before it's possible to recast them
def parserepeatactions(heroes,actions):
	removerepeats = set()
	repeats = []
	for a in actions:
		if "Repeat" in a.tags:
			repeats.append(a)
	for hid in heroes:
		# go by each hero
		rh = [r for r in repeats if r.hid == hid]
		if len(rh)>1:
			for i in range(1,len(rh)):
				if (rh[i].action == rh[i-1].action and rh[i].tid == rh[i-1].tid # if same action and target
					and rh[i].time_ms < rh[i-1].time_ms + 1000*powers[rh[i].action]['recharge_time']/config['repeat_cd_factor']): # if impossible to recast based on recharge time
					removerepeats.add(rh[i].aid)
	actions = [a for a in actions if a.aid not in removerepeats]
	return actions

def reorderactions(actions):
	actions.sort(key=lambda x: x.time_ms)
	newaid = 1
	for a in actions:
		a.aid = newaid
		newaid += 1

# store all actions and hp
def demo2data(lines,h,starttime):
	time_ms = -starttime
	actions = []
	holdactions = []
	hp = []

	match_length = config['match_length'] + config['end_buffer']
	actionid = 0
	
	for i in range(len(lines)):

		time_ms += int(lines[i][0])
		if time_ms > match_length: # end parse loop if t > 10 min
			break
		elif time_ms > -config['buff_period']: # ignore before buff timer starts

			# read per line
			hid		= lines[i][1]
			entity = lines[i][2]
			command  = lines[i][3]

			# only look at actions involving heroes. also ignores reverse powers on NPCs
			if hid in h:
				if entity == 'HP':
					currenthp = float(command)
					hploss = max(h[hid].lasthp - currenthp, 0)
					h[hid].damagetaken += hploss
					h[hid].lasthp = currenthp
					hp.append(c.Hitpoints(hid,time_ms,currenthp,hploss))

					if currenthp == 0:
						if countdeath(h[hid],time_ms):
							a = c.Action(actionid,hid,"Death",time_ms)
							a.hittime = time_ms
							a.tags.add("MOV")
							actions.append(a)
							actionid += 1
				elif entity == 'HPMAX':
					h[hid].hpmax = max(h[hid].hpmax,float(command))
				elif entity == 'POS' and lines[i][5]:
					h[hid].posrecent.append([time_ms,np.array([float(lines[i][3]),float(lines[i][4]),float(lines[i][5])])])
					h[hid].posrecent = [pos for pos in h[hid].posrecent if pos[0] > time_ms - config['pos_delay']]
					h[hid].posdelay = h[hid].posrecent[0][1]
					h[hid].poscurrent = h[hid].posrecent[-1][1]

				elif entity == 'MOV' and command in d.movs:
					a = c.Action(actionid,hid,d.movs[command],time_ms)
					a.tags.add("MOV")
					if "Death" in command or "DEATH" in command:
						if countdeath(h[hid],time_ms):
							actions.append(a)
							actionid += 1
					else:
						actions.append(a)
						actionid += 1

				elif entity == 'FX':
					line_fx = lines[i][5]
					reverse = False
					if line_fx in fx['attack'] or line_fx in fx['hit']:
						try:
							act = fx['attack'][line_fx]
						except:
							act = fx['hit'][line_fx]
							reverse = True
						tid = None
						# check next ~4 lines for target id
						a = c.Action(actionid,hid,act,time_ms)
						actionid += 1

						a = checktarget(hid,lines,h,i,a,reverse)

						# if Hold in a.tags wait until time_ms+a.recharge/3 
				
						if (
							(isinstance(a.action,str) and "NoMiss" in powers[a.action]['tags'] and a.tid) # NoMiss if power must have a target, but demo doesn't show one (e.g. blind)
							or (isinstance(a.action,list))
							or ("NoMiss" not in powers[a.action]['tags'])
							):
							actions.append(a)

					elif line_fx in fx['hold']: # if FX has multiple possible actions (e.g. entangle/thaw)
						ha = c.Action(0,hid,fx['hold'][line_fx],time_ms)
						ha = checktarget(hid,lines,h,i,ha,reverse)
						holdactions.append(ha)

	parseholdactions(actions,holdactions) # and updates power attribs
	actions = parserepeatactions(h,actions)
	determinepowersets(h,actions) # trys to guess AT and powersets based on actions done
	hponaction(hp,actions) # calcs a target's HP at hit time (estimated if not hitscan)
	phasehits(actions)
	reorderactions(actions)

	return actions,hp # not used

# merge h1 into the largest team group that h2 isn't in
def mergeintolargest(h1,h2,teams,remainders,maxteamsize):
	if h1 in remainders and h2 not in remainders:
		mergedteam = set()
		for t in teams:
			if len(t)>4 and h2 not in t and h1 not in t:
				mergedteam = t.copy()
				mergedteam.add(h1)
				teams.remove(t)
				teams = [t for t in teams if h1 not in t]
				remainders.remove(h1)
				teams.append(mergedteam)
				break
		if len(mergedteam) == maxteamsize: 
			return True,teams,remainders
	return False,teams,remainders

# apply team numbers to heroes
def applyteamnumbers(heroes,teams):
	assignteam = 0
	for h in teams[1]: # make sure first hero in demo is on team zero
		if heroes[h].firstherofound:
			assignteam = 1
			break
	# if TEAMSWAP: assignteam = abs(assignteam-1) # may not be required/manual tuning from demoparse data
	for h in teams[assignteam]:
		heroes[h].team = 0 
	assignteam = abs(assignteam-1)
	for h in teams[assignteam]:
		heroes[h].team = 1
	return

# assigns teams
def assignteams(heroes,actions):
	teams = []
	maxteamsize = math.ceil(len(heroes)/2) # assumes max # difference of one player
	oneteamfull = False
	for hid in heroes:
		teams.append({hid})

	# sort teams by friendly powers first
	for a in actions: 
		if not oneteamfull and a.tid and a.tid != a.hid: # if action has a target that isn't self 
			h1,h2 = a.hid,a.tid
			if powers[a.action]['targets_affected'] == ['Ally (Alive)']: # if action is on a teammate then put them in the same team group (merged/union)
				mergedteam = {item for t in teams for item in t if (h1 in t or h2 in t)}
				teams = [t for t in teams if (h1 not in t and h2 not in t)]
				teams.append(mergedteam)
				if len(mergedteam) == maxteamsize:
					oneteamfull = True # if one full team has been created
		if oneteamfull: # if one team's been created then merged all remaining into the same team
			mergedteam = {item for t in teams for item in t if len(t)<maxteamsize}
			teams = [t for t in teams if len(t)==maxteamsize]
			teams.append(mergedteam)
		elif len(teams) == 3 and len(heroes)%2 == 0 and min(len(teams[0]),len(teams[1]),len(teams[2]))==1: # edge case for situations where 1 player didn't buffs
			remainder = [p for t in teams for p in t if len(t) == 1][0]
			teams = [t for t in teams if remainder not in t]
			if len(teams[0]) > len(teams[1]):
				teams[1].add(remainder)
			elif len(teams[1]) > len(teams[0]):
				teams[0].add(remainder)
		if len(teams) == 2:
			applyteamnumbers(heroes,teams)
			return

	# if can't finish team assignment by friendly only then look at attacks
	remainders = [p for t in teams for p in t if len(t) <= 2] # assume most heroes get assigned properly first
	for a in actions:
		if not oneteamfull and a.tid and a.tid != a.hid: # if action has a target that isn't self 
			h1,h2 = a.hid,a.tid
			oneteamfull,teams,remainders = mergeintolargest(h1,h2,teams,remainders,maxteamsize)
			oneteamfull,teams,remainders = mergeintolargest(h2,h1,teams,remainders,maxteamsize)
		if oneteamfull: # if one team has been fully found
			mergedteam = {item for t in teams for item in t if len(t)<maxteamsize} # merge all remaining groups into the other team
			teams = [t for t in teams if len(t)==maxteamsize]
			teams.append(mergedteam)
		if len(teams) == 2:
			applyteamnumbers(heroes,teams)
			# for hid,h in heroes.items():
			# 	print(h.name,h.team)
			return

	return print('ERROR: team assignment error', teams)

# assign support tag based on criteria
def assignsupport(heroes,actions):
	for hid,h in heroes.items():
		numheals,numhealsspike  	  = 0,0
		numattacks,numattacksspike	  = 0,0
		for a in actions:
			if a.hid == hid:
				if "Heal" in a.tags and a.tid and h.team == heroes[a.tid].team:
					numheals += 1
					if a.spikeid:
						numhealsspike += 1
				elif "Attack" in a.tags:
					numattacks += 1
					if a.spikeid:
						 numattacksspike += 1
		# support criteria
		if 	(2*numheals > numattacks and 2*numhealsspike > numattacksspike
			and numheals > 10 and numhealsspike > 5): # low numbers to handle outliers I've encountered
			heroes[hid].support = 1

# did new action take place within the window since the old attack?
def isrecentaction(currenttime,oldtime,window):
	if currenttime-oldtime > window: return False
	else: return True

# return true if action is on the hid or by the hid (ignoring non-relevant toggles/etc.)
# ignore certain actions if looking for spike-relevant info only
def isactiononplayer(a,hid,tag=None):
	if tag == 'Self' and a.hid == hid and not a.tid: # self special manual tag for self powers relevant to a spike log
		if ('Phase' in a.tags or 'Teleport' in a.tags 
			or ('Heal' in a.tags and a.target_type == "Self") 
			or 'MOV' in a.tags):
			return True
	elif a.tid == hid: # action on player by other
		if tag in a.tags: # filter out non-attack offensive powers
			return True
	elif (tag == 'Teleport' or tag == 'Phase') and a.hid == hid:
		if tag in a.tags: # filter out non-attack offensive powers
			return True
	return False

# group action spikeids under the same ID if adjacent
# and extend to adjacent action if within in window
def groupactionsunderspike(hid,actions):
	lastspikeid,lastspiketime = None,None
	for a in actions:
		if isactiononplayer(a,hid,'Self') or isactiononplayer(a,hid,'Heal') or isactiononplayer(a,hid,'Attack'):
			if lastspikeid: # if first spike found
				if a.time_ms - lastspiketime < config['spike_extend_window']: # if action within cooldown on spike extend count
					a.spikeid = lastspikeid
					if "Heal" not in a.tags:
						lastspiketime = a.time_ms
				elif a.spikeid: # found new spike outside of spike window
					lastspikeid = a.spikeid # start counting from this spike
					lastspiketime = a.time_ms

			elif a.spikeid: # initialize first spike
				lastspikeid,lastspiketime = a.spikeid,a.time_ms

# update spikeids chronologically (by start) from 1
def reorderspikes(heroes,actions):
	# reorder spikeids chronologically
	spikeidmap = {}
	spikeid = 1
	for a in actions:
		if a.spikeid: # if action is tagged with a spikeid
			if a.spikeid not in spikeidmap: # if spikeid hasn't been reassigned yet
				spikeidmap[a.spikeid] = spikeid
				a.spikeid = spikeid
				if a.tid:
					heroes[a.tid].targets += 1
				else: 
					heroes[a.hid].targets += 1
				spikeid += 1
			else:
				a.spikeid = spikeidmap[a.spikeid]
	return spikeid-1

# look backwards by spike to see if same person was target last (within window)
def isspikereset(spikes,newspike,heroes):
	for i in range(newspike.sid-2,0,-1):
		if spikes[i] and i>=0:
			if heroes[newspike.tid].team == heroes[spikes[i].tid].team:
				if spikes[i].tid == newspike.tid and newspike.start - spikes[i].end < config['reset_window']:
					return True
				elif spikes[i].tid != newspike.tid:
					return False
	return False			

# returns total HP loss by a target on a spike
def spikehploss(hid,hitpoints,start,end,kill=False):
	# create a copy of latest HP in on spike start for report graphing
	insertpoint = None
	inserthp = None
	for i in range(len(hitpoints)):
		if hitpoints[i].hid == hid and hitpoints[i].time >= start:
			if i > 0 and hitpoints[i].time != start: # for errors on first spikes w/o data
				insertpoint = i
				if hitpoints[i-1].hp > 0 and hitpoints[i-1].time > hitpoints[i].time - 5000: # must be semi-recent hp
					inserthp = c.Hitpoints(hid,start,hitpoints[i-1].hp,0)
				else:
					inserthp = c.Hitpoints(hid,start,hitpoints[i].hp,0)
			break
	if insertpoint and inserthp:
		hitpoints.insert(insertpoint,inserthp)

	hploss = 0
	hplosses = [hp.hploss for hp in hitpoints if (hp.hid == hid and hp.time >= start and hp.time<=(end+config['spike_extend_window']))]
	for hp in hplosses:
		hploss += hp
	return hploss

# weighted spike determ
def weightedspikestart(recentattacks,recentjaunts,recentphases):
	attackers = set() 
	weightedscore = 0
	if recentjaunts or recentphases: # count maximum 1 jaunt or phase action towards weight
		weightedscore += 1 

	for atk in recentattacks:
		attackers.add(atk.hid)
		weightadd = 1
		if "Primary" in atk.tags:
			weightadd += 0.5
		weightedscore += weightadd
	if len(attackers) >= 2: # minimum 2 attackers to be a spike
		if len(attackers) >= 3 or weightedscore >= config['spike_weighted_score']:
			return True
	return False

# determine spikes based on attacks on heroes and flag actions as part of spikes
def flagspikeactions(heroes,actions):
	spikeid = 1000 # start at a large number since we're reordering from 1 later on

	# look at spikes for each player separately
	for hid in heroes:
		recentattacks = []
		recentprimaryattacks = []
		recentphases = []
		recentjaunts = []
		recentjauntreact = []
		for a in actions:
			if not a.spikeid: #
				if isactiononplayer(a,hid,'Attack'):
					recentattacks.append(a)
					if "Primary" in a.tags:
						recentprimaryattacks.append(a)
				elif isactiononplayer(a,hid,'Teleport'):
					recentjaunts.append(a)
				elif isactiononplayer(a,hid,'Phase'):
					recentphases.append(a)

				recentattacks = 		[x for x in recentattacks if isrecentaction(a.time_ms,x.time_ms,config['spike_init_window'])]
				recentprimaryattacks = 	[x for x in recentprimaryattacks if isrecentaction(a.time_ms,x.time_ms,config['spike_init_window']/2)]
				recentphases = 			[x for x in recentphases if isrecentaction(a.time_ms,x.time_ms,config['spike_extend_window'])]
				recentjaunts = 			[x for x in recentjaunts if isrecentaction(a.time_ms,x.time_ms,config['spike_init_window']/2)]
				recentjauntreact = 		[x for x in recentattacks if "Jaunt React" in x.tags and isrecentaction(a.time_ms,x.time_ms,config['spike_init_window']/2)] # for jauntoffone


				if (
					len(recentattacks) >= config['spike_attack_count'] # 4 any attacks in larger window
					or len(recentprimaryattacks) >= config['spike_attack_count']/2 # 4 primary attacks in smaller window
					or (len(recentjauntreact) >=1 and len(recentjaunts) >=1) # or jaunt off 1 in small window
					or weightedspikestart(recentattacks,recentjaunts,recentphases)
					):
					for recent in recentattacks: recent.spikeid = spikeid
					for recent in recentjaunts:  recent.spikeid = spikeid
					for recent in recentphases:  recent.spikeid = spikeid
					spikeid += 1
		groupactionsunderspike(hid,actions) # combine like-spikeids and extend spikes to adjacent action if appropriate

# build spike attack chain dicts for each player
def countattackchains(heroes,actions,spikes):
	for hid,h in heroes.items():
		for s in spikes:
			attacks = [a for a in actions if (
				a.spikeid == s.sid # action in spike
				and hid == a.hid # action by current hero
				and a.tid and heroes[a.tid].team != h.team # target is an enemy
				)]
			if attacks:
				attackchain = []
				for atk in attacks:
					attackchain.append(atk.action)
				attackchain = str(attackchain)
				if attackchain not in h.attackchains: h.attackchains[attackchain] = 0
				h.attackchains[attackchain] += 1
		h.attackchains = {k: v for k, v in sorted(h.attackchains.items(), key=lambda item: item[1], reverse=True)}

# for each spike calculate a new weighted spike start time based on the initial attacks
def calcspikestartdelta(actions,spikes):
	for sp in spikes:
		delta = 0.0 # delta to adjust all spike related times (ms)
		a = [x for x in actions if x.spikeid == sp.sid] # get all actions on a spike
		atks = [x for x in a if 'Attack' in x.tags] # get all attacks on a spike
		debuff_first = 0 # weight first attack lower if it's a debuff
		if 'Debuff' in atks[0].tags:
			debuff_first = 1

		atktime = [x.spiketime for x in atks if x.spiketime < (1+debuff_first)*1000.0]
		def myround(x, base=1000/30): # https://stackoverflow.com/questions/2272149/round-to-5-or-other-number-in-python
			return int(base * round(x/base))
		delta = myround(statistics.mean(atktime[0:min(3+debuff_first,len(atktime))]))

		for x in a:
			x.spiketime -= delta
			if x.spikehittime:
				x.spikehittime -= delta
		sp.start -= delta
		sp.end -= delta
		sp.startdelta = delta

# count number of attacks, attackers, heals, greens
# and timing for each attack/heal/evade
# and count first atks/heals on spikes
def calcspikestats(heroes,actions,spikes):
	for s in spikes:
		sa = [a for a in actions if s.sid == a.spikeid] # spike actions 
		attackerlist = set()
		healerlist = set()
		jaunttime = None
		phasetime = None
		first_attack = False
		first_heal = False
		for a in sa:
			if a.spikeid == s.sid:
				if 'Attack' in a.tags and 'Foe' in a.target_type:
					if not first_attack:
						first_attack = True
						heroes[a.hid].firstattacks += 1
					s.nattacks += 1
					if a.hid not in attackerlist:
						heroes[a.hid].attacktiming.append(a.spiketime) # append spiking timing to hero info
					attackerlist.add(a.hid)
				if 'Heal' in a.tags and 'Ally' in a.target_type:
					if not first_heal:
						first_heal = True
						heroes[a.hid].alphaheals += 1
					s.nheals += 1
					if a.hid not in healerlist:
						heroes[a.hid].healtiming.append(a.spiketime) # append spiking timing to hero info
					healerlist.add(a.hid)
				if 'Heal' in a.tags and 'Inspirations' in a.tags:
					s.ngreens += 1
				if a.hid == s.tid:
					if 'Phase' in a.tags and phasetime == None:
						heroes[a.hid].phasetiming.append(a.spiketime) # append spiking timing to hero info
					if 'Teleport' in a.tags and jaunttime == None:
						heroes[a.hid].jaunttiming.append(a.spiketime) # append spiking timing to hero info

		s.nattackers = len(attackerlist)



# parse spikes via actions, main function
def spikeparse(heroes,actions,hitpoints):

	flagspikeactions(heroes,actions)
	numspikes = reorderspikes(heroes,actions) # reorder cronologically (by start) from spikeid=1 and get number of spikes

	spikes = []
	spikedict = {} # create a spike object from group of spike actions
	# dict for each spikeid to access actions included
	for i in range(1,numspikes+1): 
		spikedict[i] = []
	for a in actions:
		if a.spikeid:
			spikedict[a.spikeid].append(a)

	# update start/end/duration for spikes and assign spike target
	for si,sa in spikedict.items(): # spikeid, spikeactions
		newspike = c.Spike(si)
		spikestart = 9999999999 # arbitrarily large number
		spikeend   = 0
		spikeactors = {}
		firsthit = spikestart
		for a in sa:
			if a.hittime and "Attack" in a.tags: 
				spikestart = min(spikestart,a.time_ms)
				spikeend   = max(spikeend,a.hittime)
				firsthit   = min(firsthit,a.hittime)
			if not newspike.tid and a.tid:
				newspike.tid = a.tid
				newspike.target = heroes[a.tid].name
				newspike.targetteam = heroes[a.tid].team
			if a.action == "Death":
				newspike.kill = 1
			if a.hid not in spikeactors: 
				spikeactors[a.hid] = 1
		# once timing has been determined assign relative time for each action
		# and determine action count per player
		for a in sa:
			a.spiketime = a.time_ms - spikestart
			if a.hittime:
				a.spikehittime = a.hittime - spikestart
			a.spikeactioncount = spikeactors[a.hid]
			spikeactors[a.hid] += 1

		# duration and hploss use absolute time to calculation
		# spikestart is recalculated based on certain params
		newspike.duration = spikeend - spikestart
		newspike.end = spikeend
		newspike.start = spikestart 
		newspike.hitwindow	  = spikeend - firsthit
		# todo, new spike start calc

		spikes.append(newspike)
		newspike.reset = isspikereset(spikes,newspike,heroes)

	calcspikestartdelta(actions,spikes) # calculate new spikestart based on initial attacks
	calcspikestats(heroes,actions,spikes) # various stats for spikes
	for sp in spikes: # calc hp loss after new start has been calculated
		sp.hploss = spikehploss(sp.tid,hitpoints,sp.start-sp.startdelta,sp.end,sp.kill)
	countattackchains(heroes,actions,spikes)

	return spikes

# tag heals with ff
def tagfatfingers(heroes,actions):
	for a in actions:
		if a.tid in heroes and "Heal" in a.tags and "Absorb" not in a.tags and a.target_type == "Ally (Alive)" and a.effect_area == "SingleTarget":
			if a.hithp and a.casthp:
				if a.hithp > heroes[a.tid].hpmax-2 and a.casthp > heroes[a.tid].hpmax-2 and not a.spikeid:
					a.tags.add("Fat Finger")


def parsematch(path): # primary demo parse function
	parsestart = datetime.datetime.now()

	mid = path.split('/')[-1].split('.cohdemo')[0]
	sid = path.split('/')[-2]
	score = [0,0]
	targets = [0,0]
	demomap = None

	db.createdatatables()
	db.creatematchestable()

	print('demo read: ', sid, ' ', mid)
	# PARSE LOGIC
	with open(path,'r') as demofile:
		lines,demomap = demo2lines(demofile)		
		heroes = demo2heroes(lines)
		starttime = matchstart(lines,heroes)
		actions, hp = demo2data(lines,heroes,starttime)
		assignteams(heroes,actions)
		spikes = spikeparse(heroes,actions,hp)
		assignsupport(heroes,actions)
		tagfatfingers(heroes,actions)

		# score tally
		for hid in heroes:
			score[heroes[hid].team]   += heroes[hid].deaths
			targets[heroes[hid].team] += heroes[hid].targets
		score.reverse()
		targets.reverse()
		if OVERRIDE and sid in overrides and mid in overrides[sid] and "SCORE" in overrides[sid][mid]:
			score[0]+= overrides[sid][mid]['SCORE'][0]
			score[1]+= overrides[sid][mid]['SCORE'][1]
		db.demo2db(mid,sid,hp,actions,spikes,heroes)

	print('score:     ', score)
	print('parsetime: ', str(datetime.datetime.now() - parsestart)) # parse runtime

	db.insertsql("Matches",[mid,sid,demomap,0,score[0],score[1],targets[0],targets[1]])
	return score
	



def parseseries(path): # parse series (i.e. single date folder full of demos)
	db.createseriestable()

	matches = [m for m in os.listdir(path) if m.endswith(".cohdemo")]
	matches.sort()

	record = [0,0,0]
	series_kb = False
	for m in matches:
		score = parsematch(os.path.join(path, m))
		if score[0] > score[1]:
			record[0] += 1
		elif score[0] == score[1]:
			record[2] += 1
		else:
			record[1] += 1

	# series data from folder name
	seriesid = path.split('/')[-1]
	seriesdate = seriesid.split('_')[0]
	seriesdate = '20' + seriesdate[0:2] + '-' + seriesdate[2:4]  + '-' + seriesdate[4:6]
	serieskb = 0
	if 'kb' in seriesid:
		serieskb = 1
	team1, team2 = None, None
	if serieskb == 0 and len(seriesid.split('_'))>2:
		team1,team2 = seriesid.split('_')[1], seriesid.split('_')[2]

	db.deletesql("Series",seriesid) # delete db data if already existing prior to rewriting
	db.insertsql("Series",[seriesid,seriesdate,serieskb,team1,team2,record[0],record[1],record[2]])

	# return seriesdate,serieskb
	

	
def parseall(path): # parse collection (i.e. folder full of series)
	series = [s for s in os.listdir(path) if not os.path.isfile(os.path.join(path, s))] # only iterate folders in path
	series.sort()
	for s in series:
		parseseries(os.path.join(path, s))
	return
		
def main():
	# parse command line arguments
	argp = argparse.ArgumentParser(description='Parse .cohdemos to a database file.')
	argp.add_argument('-a','--all',		action="store",	dest = 'path', 		help='parse all series in path')
	argp.add_argument('-s','--series',	action="store",	dest = 'seriespath',help='parse all matches in series folder')
	argp.add_argument('-m','--match',	action="store",	dest = 'matchpath', help='parse a single match')
	args = argp.parse_args()
	
	# parse by command arg type, assumes correct user path inputs
	if args.path:
		parseall(os.path.abspath(args.path))
	elif args.seriespath:
		parseseries(os.path.abspath(args.seriespath))
	elif args.matchpath:
		parsematch(os.path.abspath(args.matchpath))
	else: # no input or wrong args
		argp.print_help()
		return

	if HERODUMP:
		herodump_undefined = {}
		herodump_defined = {}
		for hero,val in herodump.items():
			if 'archetype' not in herodump[hero] and 'sets' not in herodump[hero]:
				herodump_undefined[hero] = {}
			else:
				herodump_defined[hero] = val
		with open('data/herodump_defined.json','w') as f:
			json.dump(herodump_defined,f,indent=4,sort_keys=True)
		with open('data/herodump_undefined.json','w') as f:
			json.dump(herodump_undefined,f,indent=4,sort_keys=True)
	
	db.con.commit()
	db.con.close()


if __name__ == '__main__':
	main()
