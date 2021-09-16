#!/usr/bin/env python

import os, sys, time, math, argparse, datetime

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

# for parsing existing demos to find overrides I put in
overrides     	= []
try:
	overridesdump = json.loads(open('data/overridesdump.json').read())
except:
	overridesdump = {}
try:
	herodump = json.loads(open('data/herodump.json').read())
except:
	herodump = {}

# converts demo file to list
def demo2lines(demo):
	line = [p.replace('\n','').replace('\"','') for p in re.split("( |\\\".*?\\\"|'.*?')", demo.readline()) if p.strip()] # from https://stackoverflow.com/questions/79968/split-a-string-by-spaces-preserving-quoted-substrings-in-python
	lines = [line]
	demomap = None
	while line:
		line = [p.replace('\n','').replace('\"','') for p in re.split("( |\\\".*?\\\"|'.*?')", demo.readline()) if p.strip()]
		if 'OVERRIDE' in line: # parse existing overrides from demoparse formatting
			overrides.append({line[3]:line[4:]})
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
	return lines,demomap

# returns player names and ids from demo
def demo2heroes(lines):
	heroes = {}
	npcs = []
	for i in range(min(30000,len(lines))): # should find all heroes by 30k lines
		if lines[i][2] == "NPC" and lines[i][3] not in d.ignorecostumes:
			npcs.append(lines[i][1])
		if lines[i][2] == "NEW" and lines[i][1] not in npcs:
			name = lines[i][3]
			hid = lines[i][1]
			if name not in d.namefilter and name not in heroes and i < len(lines) - 6:
				isnpc = False
				for j in range(5): # check next 5 lines for NPC tag
					if lines[i+j][1] == hid and lines[i+j][2] == 'NPC':
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
	a.tags = powers[a.action]['tags']
	a.target_type = powers[a.action]['target_type']
	if "Delay" in powers[a.action]['tags']:
		a.time_ms -= powers[a.action]['frames_before_hit']
	if a.tid and a.dist:
		a.hittime = a.time_ms + int(1000*powers[a.action]['frames_before_hit']+a.dist/powers[a.action]['projectile_speed'])
	else:
		a.hittime = a.time_ms + int(1000*powers[a.action]['frames_before_hit'])
	a.roottime = a.time_ms + int(1000*powers[a.action]['frames_attack'])

# handle hold actions waiting to be determined
def parseholdactions(actions,holdactions):
	for a in actions:
		if isinstance(a.action,list): # for every actions with undefined power
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
				a.hittime = a.time_ms + int(1000*powers[a.action]['frames_before_hit']+a.dist/powers[a.action]['projectile_speed'])
			else:
				a.hittime = a.time_ms + int(1000*powers[a.action]['frames_before_hit'])
		if "MOV" not in a.tags:
			updateactionattribs(a)

	# remove all actions with undefined powers (.action is a list)
	actions = [a for a in actions if not isinstance(a.action,list)]

def determinearchetypes(heroes,actions):
	for hid,h in heroes.items():
		# possible_ats = {"arachnos_soldier","arachnos_widow","blaster","brute","controller","corruptor","defender","dominator","mastermind","peacebringer","scrapper","sentinel","stalker","tanker","warshade"}
		possible_ats = {"arachnos_soldier","arachnos_widow","blaster","brute","controller","defender/corruptor","dominator","mastermind","peacebringer","scrapper","sentinel","stalker","tanker","warshade"}
		for a in actions: # loop until end or 2 powersets determined
			if hid == a.hid and a.action in powers and len(powers[a.action]['archetypes'])>0:
				possible_ats = possible_ats.intersection(set(powers[a.action]['archetypes']))
			if len(possible_ats) == 1:
				h.archetype = max(possible_ats)

				# log a determined AT if found and not from a previous demo
				if h.name in herodump:
					if "archetype" not in herodump[h.name]:
						herodump[h.name]['archetype'] = h.archetype
				else:
					herodump[h.name] = {'archetype':h.archetype}

				break

		h.possible_ats = possible_ats

		# if no AT determined look if it was found in another demo
		if not h.archetype:
			if h.name in herodump and 'archetype' in herodump[h.name]:
				h.archetype = herodump[h.name]['archetype']
		# print(h.name,' ',h.possible_ats)


def determinepowersets(heroes,actions):
	determinearchetypes(heroes,actions)
	for hid,h in heroes.items():
		for a in actions: # loop until end or 2 powersets determined
			if hid == a.hid and len(h.sets) < 2 and a.action in powers: # if valid action by hid
				psets = powers[a.action]['powersets'] # possible power sets for action
				# check valid powersets for calculated h.possible_ats
				possible_psets = set()
				for ps in psets:
					ps_ats = set(powers['powersets'][ps]) # ATs that can use pset
					if len(ps_ats.intersection(h.possible_ats)) > 0: # does the pset AT have anything incommon with the determined ATs?
						possible_psets.add(ps) # if true then the pset is valid
				psets = [ps for ps in psets if ps in possible_psets] # remove non-valid powersets
				if (len(psets) == 1 and psets[0] not in h.sets and len(powers[a.action]['archetypes'])<14): # ignore epic/pool/temp/insps
					h.sets.add(psets[0])
			if len(h.sets) == 2:
				break

	for hid,h in heroes.items():
		# if sets are determined log it in 
		if len(h.sets) == 2:
			if h.name in herodump:
				if 'sets' not in herodump[h.name]:
					herodump[h.name]['sets'] = list(h.sets)
			else:
				herodump[h.name] = {'sets':list(h.sets)}
		# otherwise look if sets have been found before
		else:
			if h.name in herodump and 'sets' in herodump[h.name]:
				h.sets = set(herodump[h.name]['sets'])
	# 	# print(h.name,' ',h.sets)

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

			if hid in h:
				if entity == 'HP':
					currenthp = float(command)
					hploss = max(h[hid].lasthp - currenthp, 0)
					h[hid].damagetaken += hploss
					h[hid].lasthp = currenthp
					hp.append([time_ms,hid,currenthp,hploss])

					if currenthp == 0:
						if countdeath(h[hid],time_ms):
							a = c.Action(actionid,hid,"Death",time_ms)
							a.tags.append("MOV")
							actions.append(a)
							actionid += 1
				elif entity == 'HPMAX':
					h[hid].hpmax == max(h[hid].hpmax,float(command))
				elif entity == 'POS' and lines[i][5]:
					h[hid].posrecent.append([time_ms,np.array([float(lines[i][3]),float(lines[i][4]),float(lines[i][5])])])
					h[hid].posrecent = [pos for pos in h[hid].posrecent if pos[0] > time_ms - config['pos_delay']]
					h[hid].posdelay = h[hid].posrecent[0][1]
					h[hid].poscurrent = h[hid].posrecent[-1][1]

				elif entity == 'MOV' and command in d.movs:
					a = c.Action(actionid,hid,d.movs[command],time_ms)
					a.tags.append("MOV")
					if "Death" in command or "DEATH" in command:
						if countdeath(h[hid],time_ms):
							actions.append(a)
							actionid += 1
					else:
						actions.append(a)
						actionid += 1

				elif entity == 'FX':
					if lines[i][5] in fx['attack'] or lines[i][5] in fx['hit']:
						reverse = False
						try:
							act = fx['attack'][lines[i][5]]
						except:
							act = fx['hit'][lines[i][5]]
							reverse = True
						tid = None
						## if action == 'OneShot'/'Maintained': # if check needed with fx system?
						# check next ~4 lines for target id
						a = c.Action(actionid,hid,act,time_ms)
						if isinstance(act,str) and "Delay" in powers[a.action]['tags']:
							a.time_ms -= powers[act]['frames_before_hit']
						actionid += 1

						
						for j in range(4): # check for target
							if lines[i+j][1] == hid and lines[i+j][2] == 'TARGET' and lines[i+j][3] == 'ENT':
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
								break

						# if Hold in a.tags wait until time_ms+a.recharge/3 
						actions.append(a)

					elif lines[i][5] in fx['hold']: # if FX has multiple possible actions (e.g. entangle/thaw)
						ha = c.Action(0,hid,fx['hold'][lines[i][5]],time_ms)
						if "Delay" in powers[a.action]['tags']:
							ha.time_ms -= powers[ha.action]['frames_before_hit']
						for j in range(4): # check for target
							if lines[i+j][1] == hid and lines[i+j][2] == 'TARGET' and lines[i+j][2] == 'POS':
								tidtmp = lines[i+j][4]
								if tidtmp in p and tidtmp != hid:
									ha.tid = tidtmp
								break
						holdactions.append(ha)

	parseholdactions(actions,holdactions)
	determinepowersets(h,actions)

	return actions,hp # not used

# assigns teams
def assignteams(lines,heroes,actions):
	teams = []
	for hid in heroes:
		teams.append({hid})

	for a in actions: # sort teams by friendly powers first
		if a.tid and a.tid != a.hid: # if action has a target that isn't self 
			h1,h2 = a.hid,a.tid
			if powers[a.action]['targets_affected'] == ['Ally (Alive)']: # if action is on a teammate then put them in the same team group (merged/union)
				mergedteam = {item for t in teams for item in t if (h1 in t or h2 in t)}
				teams = [t for t in teams if (h1 not in t and h2 not in t)]
				teams.append(mergedteam)
			# elif len(teams)<4 and powers[a.action]['targets_affected'] == ['Foe (Alive)']: # if action is solely an attack/offence, len < 5 only use when support powers not working well
				# add h1/2 who isn't assigned a team to the largest team that h2/1 isn't on
		if len(teams) == 3 and min(len(teams[0]),len(teams[1]),len(teams[2]))==1: # edge case for situations where 1 player didn't buffs
			remainder = [p for t in teams for p in t if len(t) == 1][0]
			teams = [t for t in teams if remainder not in t]
			if len(teams[0]) > len(teams[1]):
				teams[1].add(remainder)
			elif len(teams[1]) > len(teams[0]):
				teams[0].add(remainder)
		if len(teams) == 2:
			assignteam = 0
			for h in teams[1]: # make sure first hero in demo is on team zero
				if heroes[h].firstherofound:
					assignteam = 1
			for h in teams[assignteam]:
				heroes[h].team = 0 
				# print()
			assignteam = abs(assignteam-1)
			for h in teams[assignteam]:
				heroes[h].team = 1
			return
	return print('ERROR: team assignment error')

# did new action take place within the window since the old attack?
def isrecentaction(currenttime,oldtime,window):
	if currenttime-oldtime > window: return False
	else: return True

def jauntoffonecheck(attacklist,window):
	jaunttime = None
	for a in attacklist:
		if "Teleport" in a.tags:
			jaunttime = a.time_ms
			break
	if jaunttime:
		for a in attacklist:
			if "Teleport" not in a.tags and "Jaunt React" in a.tags:
				if abs(a.time_ms-jaunttime) < window: return True
	return False

# return true if action is on the hid or by the hid (ignoring non-relevant toggles/etc.)
# ignore certain actions if looking for spike-relevant info only
def isactiononplayer(a,hid,onself=False):
	if onself and a.hid == hid and not a.tid: # action by self on Null
		if 'Phase' in a.tags or 'Teleport' in a.tags or ('Heal' in a.tags and a.target_type == "self") or 'MOV' in a.tags:
			return True
	elif a.tid == hid: # action on player by other
		if 'Attack' in a.tags: # filter out non-attack offensive powers
			return True
	return False

# group action spikeids under the same ID if adjacent
# and extend to adjacent action if within in window
def groupactionsunderspike(hid,p_actions):
	lastspikeid,lastspiketime = None,None
	for a in p_actions:
		if lastspikeid: # if first spike found
			if a.time_ms - lastspiketime < config['spike_extend_window']: # if action within cooldown on spike extend count
				if isactiononplayer(a,hid,onself=True):
					a.spikeid = lastspikeid
					lastspiketime = a.time_ms
			elif a.spikeid: # found new spike outside of spike window
				lastspikeid = a.spikeid # start counting from this spike
				lastspiketime = a.time_ms

		elif a.spikeid: # initialize first spike
			lastspikeid,lastspiketime = a.spikeid,a.time_ms
	return p_actions

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

def isspikereset(spikes,newspike,heroes):
	for i in range(newspike.sid-2,0,-1):
		if spikes[i] and i>=0:
			if heroes[newspike.tid].team == heroes[spikes[i].tid].team:
				if spikes[i].tid == newspike.tid and newspike.start - spikes[i].end < config['reset_window']:
					return True
				elif spikes[i].tid != newspike.tid:
					return False
	return False			

# parse spikes via actions, main function
def spikeparse(lines,heroes,actions,hp):
	spikes = []
	spikeid = 1000 # start at a large number since we're reordering from 1 later on

	# look at spikes for each player separately
	for hid, p in heroes.items():

		# split out actions by player
		p_actions = []
		for a in actions: 
			if isactiononplayer(a,hid,onself=True):
				p_actions.append(a) #
		recentattacks = []
		recentprimaryattacks = []
		recentheals = []

		# go through actions by player, tags spike starts
		for a in p_actions:
			if not a.spikeid:
				if isactiononplayer(a,hid):
					recentattacks.append(a)
					if "Primary" in a.tags:
						recentprimaryattacks.append(a)

				recentattacks = [x for x in recentattacks if isrecentaction(a.time_ms,x.time_ms,config['spike_init_window'])]
				recentprimaryattacks = [x for x in recentprimaryattacks if isrecentaction(a.time_ms,x.time_ms,config['spike_init_window']/2)]
				jauntoffone = jauntoffonecheck(recentattacks,config['spike_init_window']/2)

				if len(recentattacks) >= config['spike_attack_count'] or len(recentprimaryattacks) >= config['spike_attack_count']/2 or jauntoffone: # and len(recentenemies) > config['spike_enemy_count']) or recentweighted > config['spike_weighted_count']
					for aa in recentattacks:
						aa.spikeid = spikeid
					spikeid += 1

		groupactionsunderspike(hid,p_actions) # combine like-spikeids and extend spikes to adjacent action if appropriate

	numspikes = reorderspikes(heroes,actions) # reorder cronologically from spikeid=1
	spikedict = {} # create a spike object from group of spike actions
	for i in range(1,numspikes+1): spikedict[i] = []
	for a in actions:
		if a.spikeid:
			spikedict[a.spikeid].append(a)
	for si,sa in spikedict.items(): # spikeid, spikeactions
		newspike = c.Spike(si)
		spikestart = 9999999999 # arbitrarily large int
		spikeend   = 0
		for a in sa:
			spikestart = min(spikestart,a.time_ms)
			if a.hittime and "Attack" in a.tags: 
				spikeend   = max(spikeend,a.hittime)
			if not newspike.tid and a.tid:
				newspike.tid = a.tid
				newspike.tname = heroes[a.tid].name
			if a.action == "Death":
				newspike.kill = 1
			# TODO reset for loop backwards on spikes list
		newspike.start = spikestart
		newspike.end = spikeend
		newspike.duration = spikeend - spikestart
		spikes.append(newspike)
		newspike.reset = isspikereset(spikes,newspike,heroes)
			

	return spikes


def parsematch(path): # primary demo parse function
	parsestart = datetime.datetime.now()

	mid = path.split('/')[-1].split('.cohdemo')[0]
	sid = path.split('/')[-2]
	score = [0,0]

	db.createdatatables()

	# PARSE LOGIC
	with open(path,'r') as demofile:
		# override = yaml.safe_load(open(path.replace('.cohdemo','.override')))
		lines,demomap = demo2lines(demofile)		
		heroes = demo2heroes(lines)
		starttime = matchstart(lines,heroes)
		actions, hp = demo2data(lines,heroes,starttime)
		assignteams(lines,heroes,actions)
		spikes = spikeparse(lines,heroes,actions,hp)

		for hid in heroes:
			score[heroes[hid].team] += heroes[hid].deaths
		score.reverse()
		db.demo2db(mid,sid,hp,actions,spikes,heroes)

	for o in overrides:
		overridesdump[sid+'/'+mid] = o

	print('score:     ', score)
	print('demo read: ', sid, ' ', mid)
	print('lines run: ', len(lines)) # parse runtime
	print('parsetime: ', str(datetime.datetime.now() - parsestart)) # parse runtime
	return score
	

def parseseries(path): # parse series (i.e. single date folder full of demos)
	db.creatematchestable()

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
	if serieskb == 0:
		team1,team2 = seriesid.split('_')[1], seriesid.split('_')[2]

	

	db.insertsql("Series",[seriesid,seriesdate,serieskb,team1,team2,record[0],record[1],record[2]])

	# return seriesdate,serieskb
	
def parseall(path): # parse collection (i.e. folder full of series)
	db.createseriestable()
	series = [s for s in os.listdir(path) if not os.path.isfile(os.path.join(path, s))] # only iterate folders in path
	series.sort()
	for s in series:
		parseseries(os.path.join(path, s))


	with open('data/overridesdump.json','w') as f:
		json.dump(overridesdump,f,indent=4)
	with open('data/herodump.json','w') as f:
		json.dump(herodump,f,indent=4)

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

	# con.close()



if __name__ == '__main__':
	main()
