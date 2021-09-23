import sqlite3 as sqldb
# import duckdb as sqldb

con = sqldb.connect('demos.db')
cur = con.cursor()

# functions to write to db
def insertsql(table,items):
	sql = "INSERT INTO " + table + " VALUES(" + (len(items)-1)*"?," + "?)"
	cur.execute(sql, items)
	# if table == 'Series' or table == 'Matches':
		# con.commit()

def deletesql(table,sid,mid=None):
	sql = "DELETE from " + table + " WHERE series_id=?"
	items = [sid]
	if mid:
		sql += " and match_id=?"
		items.append(mid)
	cur.execute(sql,items)


# db table structure, match level
def createdatatables():
	cur.execute('''CREATE TABLE IF NOT EXISTS Actions (
				action_id INT,
				match_id INT,
				series_id TEXT, 
				action_time REAL, 
				actor TEXT, 
				action TEXT, 
				target TEXT, 
				hit_time REAL, 
				hit_hp REAL, 
				cast_dist REAL, 
				root_time REAL, 
				spike_id INT, d
				spike_time REAL, 
				spike_hit_time REAL, 
				spike_action_number INT, 
				action_tags TEXT, 
				PRIMARY KEY (action_id,series_id, match_id));
				''')
	cur.execute('''CREATE TABLE IF NOT EXISTS Spikes (
				spike_id INT, 
				match_id INT,
				series_id TEXT, 
				spike_start REAL, 
				spike_duration REAL, 
				target TEXT, 
				target_team TEXT, 
				spike_hp_loss REAL, 
				kill INT, 
				reset TEXT, 
				PRIMARY KEY (spike_id, series_id, match_id));
				''')
	cur.execute('''CREATE TABLE IF NOT EXISTS Heroes (
				hero TEXT, 
				h_id TEXT, 
				match_id INT,
				series_id TEXT, 
				team INT, 
				player_name TEXT, 
				set1 TEXT, 
				set2 TEXT, 
				archetype TEXT,
				support INT, 
				damage_taken REAL, 
				deaths INT, 
				targets INT,
				attack_chains TEXT,
				PRIMARY KEY (hero, series_id, match_id));
				''')
	cur.execute('''CREATE TABLE IF NOT EXISTS HP (
				match_time REAL, 
				hero TEXT, 
				match_id INT,
				series_id TEXT, 
				hp REAL, 
				hp_loss REAL, 
				PRIMARY KEY (match_time, hero, series_id, match_id));
				''')
def creatematchestable():
	cur.execute('''CREATE TABLE IF NOT EXISTS Matches (
				match_id INT,
				series_id TEXT, 
				map TEXT, 
				match_time REAL, 
				score0 INT, 
				score1 INT, 
				spikes0 INTEGER, 
				spikes1 INTEGER,
				PRIMARY KEY(match_id, series_id));
				''')
def createseriestable():
	cur.execute('''CREATE TABLE IF NOT EXISTS Series (
				series_id TEXT PRIMARY KEY,
				seriesdate TEXT, 
				kb INTEGER, 
				team0 TEXT, 
				team1 TEXT, 
				score1 INTEGER, 
				score2 INTEGER, 
				score3 INTEGER);''')

def demo2db(mid,sid,hp,actions,spikes,heroes):
	cleardemoentries(mid,sid)
	for h in hp:
		insertsql("HP",[h.time,heroes[h.hid].name,mid,sid,h.hp,h.hploss])
	for a in actions:
		target = None
		if a.tid: target = heroes[a.tid].name
		insertsql("Actions",[a.aid,mid,sid,a.time_ms,heroes[a.hid].name,a.action,target,a.hittime,a.hithp,a.dist,a.roottime,a.spikeid,a.spiketime,a.spikehittime,a.spikeherocount,str(a.tags)])
	for s in spikes:
		insertsql("Spikes",[s.sid,mid,sid,s.start,s.duration,s.target,s.targetteam,s.hploss,s.kill,s.reset])
	for hid,h in heroes.items():
		insertsql("Heroes",[h.name,h.hid,mid,sid,h.team,h.playername,str(h.sets),h.set2,h.archetype,h.support,h.damagetaken,h.deaths,h.targets,str(h.attackchains)])
	# con.commit()

# if reparsing an existing db entry, delete and redo
def cleardemoentries(mid,sid):
	deletesql("Matches",sid,mid)
	deletesql("HP",sid,mid)
	deletesql("Actions",sid,mid)
	deletesql("Spikes",sid,mid)
	deletesql("Heroes",sid,mid)
	con.commit()