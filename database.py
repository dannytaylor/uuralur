import sqlite3 as sqldb
# import duckdb as sqldb

con = sqldb.connect('demos.db')
cur = con.cursor()

# def insertaction(actionid,mid,sid,time,actor,action,target,hittime,dist,roottime,spikeid):
# 	sql = "REPLACE INTO Actions VALUES(?, ?,	 ?, ?, ?, ?, ?, ?, ?, ?, ?)"
# 	cur.execute(sql, (actionid,mid,sid,time,actor,action,target,hittime,dist,roottime,spikeid))
# 	return
# def inserthp(matchtime,name,mid,sid,hp,hploss):
# 	sql = "REPLACE INTO HP VALUES(?, ?, ?, ?, ?, ?)"
# 	cur.execute(sql, (matchtime,name,mid,sid,hp,hploss))
# 	return
# def insertspike(spikeid,mid,sid,start,target):
# 	sql = "REPLACE INTO Spikes VALUES(?, ?, ?, ?, ?)"
# 	cur.execute(sql, (spikeid,mid,sid,start,target))
# 	return
# def inserthero(name,hid,mid,sid,team,playername,set1,set2,archetype,hpmax,support,hploss,targets,deaths):
# 	sql = "REPLACE INTO Heroes VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
# 	cur.execute(sql, (name,hid,mid,sid,team,playername,set1,set2,archetype,hpmax,support,hploss,targets,deaths))
# 	return
# def insertmatch(mid,sid,matchtime,map,score1,score2,targets1,targets2):
# 	sql = "REPLACE INTO Matches VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)"
# 	cur.execute(sql, (mid,sid,matchtime,map,score1,score2,targets1,targets2))
# 	con.commit()
# 	return
# def insertseries(sid,date,kb,team1,team2,win,loss,tie):
# 	sql = "REPLACE INTO Series VALUES(?, ?, ?, ?, ?, ?, ?, ?)"
# 	cur.execute(sql, (sid, date,kb,team1,team2,win,loss,tie))
# 	con.commit()
# 	return

# functions to write to db
def insertsql(table,items):
	sql = "REPLACE INTO " + table + " VALUES(" + (len(items)-1)*"?," + "?)"
	cur.execute(sql, items)
	if table == 'Series' or table == 'Matches':
		con.commit()

# db table structure, match level
def createdatatables():
	cur.execute('''CREATE TABLE IF NOT EXISTS Actions (
				actionid INT, 
				matchid INT,
				seriesid TEXT, 
				actiontime REAL, 
				actor TEXT, 
				action TEXT, 
				target TEXT, 
				hittime REAL, 
				dist REAL, 
				roottime REAL, 
				spikeid INT, 
				PRIMARY KEY (actionid, seriesid, matchid));
				''')
	cur.execute('''CREATE TABLE IF NOT EXISTS Spikes (
				spikeid INT, 
				matchid INT,
				seriesid TEXT, 
				spikestart REAL, 
				actor TEXT, 
				PRIMARY KEY (spikeid, seriesid, matchid));
				''')
	cur.execute('''CREATE TABLE IF NOT EXISTS Heroes (
				hero TEXT, 
				hid TEXT, 
				matchid INT,
				seriesid TEXT, 
				team INT, 
				playername TEXT, 
				set1 TEXT, 
				set2 TEXT, 
				archetype TEXT, 
				maxhp REAL, 
				supportid INT, 
				damagetaken REAL, 
				targets INT, 
				deaths INT, 
				PRIMARY KEY (hero, seriesid, matchid));
				''')
	cur.execute('''CREATE TABLE IF NOT EXISTS HP (
				matchtime REAL, 
				hero TEXT, 
				matchid INT,
				seriesid TEXT, 
				hp REAL, 
				hploss REAL, 
				PRIMARY KEY (matchtime, hero, seriesid, matchid));
				''')
def creatematchestable():
	cur.execute('''CREATE TABLE IF NOT EXISTS Matches (
				matchid INT,
				seriesid TEXT, 
				map TEXT, 
				matchtime REAL, 
				score1 INT, 
				score2 INT, 
				targets1 INTEGER, 
				targets2 INTEGER,
				PRIMARY KEY(matchid, seriesid));
				''')
def createseriestable():
	cur.execute('''CREATE TABLE IF NOT EXISTS Series (
				seriesid TEXT PRIMARY KEY,
				seriesdate TEXT, 
				kb INTEGER, 
				team1 TEXT, 
				team2 TEXT, 
				score1 INTEGER, 
				score2 INTEGER, 
				score3 INTEGER);''')

def demo2db(mid,sid,hp,actions,spikes,heroes):
	for h in hp:
		insertsql("HP",[h[0],heroes[h[1]].name,mid,sid,h[2],h[3]])
	for a in actions:
		target = None
		if a.tid: target = heroes[a.tid].name
		insertsql("Actions",[a.aid,mid,sid,a.time_ms,heroes[a.hid].name,a.action,target,a.hittime,a.dist,a.roottime,a.spikeid])
	for s in spikes:
		insertsql("Spikes",[s.sid,mid,sid,s.start,s.tname])
	for hid,h in heroes.items():
		insertsql("Heroes",[h.name,h.hid,mid,sid,h.team,h.playername,str(h.sets),h.set2,h.archetype,h.hpmax,h.support,h.damagetaken,h.targets,h.deaths])
	con.commit()