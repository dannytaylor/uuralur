import os, sys, time, math, argparse, json, datetime, yaml, sqlite3

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import numpy as np
import tools.util as util

import plotly.express as px
import plotly.graph_objects as go

# sqlite connections
con = sqlite3.connect('demos.db')
cur = con.cursor()

# global vars/config
config = yaml.safe_load(open('data/config.yaml'))
h2p    = json.loads(open('data/hero2player.json').read())

# setup global vars for st
if "sid" not in ss: ss.sid = []
if "mid" not in ss: ss.mid = []
if "view" not in ss: ss.view = {}

# setup series/match multiselect dataframes
if 'series' not in ss:	
	ss.series 		= pd.read_sql_query("SELECT * FROM Series", con)
	ss.series['date'] = pd.to_datetime(ss.series['series_date'])
	ss.series['date'] = ss.series['date'].dt.date
if 'matches' not in ss:
	ss.matches 			= pd.read_sql_query("SELECT * FROM Matches", con)



# filter series by settings
def series_filters():
	dates_expander = st.sidebar.expander('series options',expanded=False)
	series_filters = {}
	with dates_expander:
		dates = ss.series['date'].tolist()
		series_filters['date_first'] = st.date_input('first date',value=dates[0],min_value=dates[0],max_value=dates[-1])
		series_filters['date_last']  = st.date_input('last date',value=dates[-1],min_value=series_filters['date_first'] ,max_value=dates[-1])
		series_filters['match_type']   = st.radio('match types',['all','scrims','kickball'],help="Scrims are any non-kickball/community series")
	series_filtered = ss.series[(ss.series['date'] >= series_filters['date_first']) & (ss.series['date'] <= series_filters['date_last'])]

	# filter series by series type
	if series_filters['match_type'] == 'scrims':
		series_filtered = series_filtered[series_filtered['kb'] == 0]
	elif series_filters['match_type'] == 'kickball':
		series_filtered = series_filtered[series_filtered['kb'] == 1]

	return series_filtered



def sidebar():
	pickers = st.sidebar.container()
	
	sid_filtered = series_filters() # filter series for selecting by options
	ss.sid = pickers.multiselect("series",sid_filtered)

	# only show MID picker if single SID selected
	if len(ss.sid) == 1:
		sid = ss.sid[0]
		sid_matches = ss.matches[ss.matches['series_id'] == sid] # update match list for SID only
		
		# format text to display map name in multiselect
		sid_mids = sid_matches['match_id'].tolist()
		sid_matches = sid_matches.set_index('match_id') # update match list for SID only
		def format_mid_str(mid):
			return str(mid) + " (" + sid_matches.loc[mid,'map'] + ")"
		
		ss.mid = pickers.multiselect("matches",sid_mids,format_func=format_mid_str) 
	else:
		ss.mid = []

	ss.view = {util.set_view_mode(ss.sid,ss.mid) : None} # set viewer mode based on selections

	navigator = st.sidebar.container()
	with navigator:
		if 'match' in ss.view:
			ss.view['match'] = st.radio('navigator',['summary','spikes','offence','defence','logs'])


def body():


	if 'match' in ss.view:
		# high level score,map,etc. to go hero
		
		sqlq = util.str_sqlq('Heroes',ss.sid[0],ss.mid[0])
		hero_df = pd.read_sql_query(sqlq, con)
		hero_list = hero_df['hero'].tolist()

		sqlq = util.str_sqlq('Actions',ss.sid[0],ss.mid[0])
		actions_df = pd.read_sql_query(sqlq, con)
		actions_df['time'] = pd.to_datetime(actions_df['time_ms'],unit='ms').dt.strftime('%M:%S')


		# START SUMMARY PAGE
		if ss.view['match'] == 'summary':
			hdf = hero_df[['hero','team','archetype','set1','set2','deaths','targets']].copy()
			teammap = {0:'🔵',1:'🔴'}
			hdf['team'] = hdf['team'].map(teammap)
			hdf = hdf.set_index(['hero','team'])
			st.table(hdf.style.format(na_rep='-'))
		# END SUMMARY PAGE


		# START SPIKES
		elif ss.view['match'] == 'spikes':
			c1,c2 = st.columns(2)

			# left side
			with c1:
				# get spike data for match
				sqlq = util.str_sqlq('Spikes',ss.sid[0],ss.mid[0],columns=['spike_id','time_ms','spike_duration','target','target_team','spike_hp_loss','kill'])
				df = pd.read_sql_query(sqlq, con)
				df = df.rename(columns={"time_ms": "time", "spike_duration": "dur", "spike_id": "#","spike_hp_loss": "dmg","target_team": "team"})
				df['time'] = pd.to_datetime(df['time'],unit='ms').dt.strftime('%M:%S')

				# select individual spikes
				st_spikes = st.empty()

				# spike filters
				filters = st.expander('spike filters',expanded=False)
				spike_filters = {}
				with filters:
					spike_filters['players'] = st.multiselect('heroes',hero_list)
					spike_filters['team'] = st.radio('team',['all','blue','red'])
					spike_filters['deaths'] = st.radio('deaths',['all','dead','alive'])
				sf = df # spikes filtered dataframe copy
				if spike_filters['players']: # if 1+ players are selected
					sf = sf[sf['target'].isin(spike_filters['players'])]
				if spike_filters['team'] == 'blue':
					sf = sf[(sf['team'] == '0')]
				elif spike_filters['team'] == 'red':
					sf = sf[(sf['team'] == '1')]
				if spike_filters['deaths'] == 'dead':
					sf = sf[(sf['kill'] == 1)]
				elif spike_filters['deaths'] == 'alive':
					sf = sf[(sf['kill'] != 1)]

				# format selection text for spikes
				# select spike for rightside viewing
				def format_spike_str(spid):
					text = '[' + sf.loc[spid-1,'time'] + '] ' + sf.loc[spid-1,'target']
					if sf.loc[spid-1,'kill'] == 1:
						text += " 💀"
					return text
				spid = st_spikes.selectbox('select spike',sf,format_func=format_spike_str) # select from filtered
				
				# format data for printing table
				killmap = {0:'',1:'💀'}
				teammap = {'0':'🔵','1':'🔴'}
				sf['team'] = sf['team'].map(teammap)
				sf['kill'] = sf['kill'].map(killmap)
				sf['dur'] = sf['dur']/1000
				sf['dmg'] = sf['dmg'].astype(int)

				sf_write = sf[['time','target','team','dur','kill','dmg']]
				sf_write = sf_write.set_index(['time','target'])		
				st.dataframe(sf_write.style.format(precision=1,na_rep=' '),height=600)

			# right side
			with c2:
				# grab actions with spike id
				sl = actions_df[(actions_df['spike_id'] == spid)] # spike log
				
				# format spike dataframe
				sl = sl.rename(columns={"time": "match_time", "spike_time": "time", "spike_hit_time": "hit", "cast_dist": "dist"})
				sl['time'] = sl['time']/1000
				sl['hit'] = sl['hit']/1000
				sl['hit_hp'] = sl['hit_hp'].fillna(-1).astype(int).replace(-1,pd.NA)
				sl['dist'] = sl['dist'].fillna(-1).astype(int).replace(-1,pd.NA)
				sl_write = sl[['match_time','actor','action','time','hit','dist','hit_hp']]
				sl_write = sl_write.set_index(['match_time','actor','action'])		

				st.dataframe(sl_write.style.format(precision=2,na_rep=' '),height=800)

		# END SPIKES



def main():
	st.set_page_config(
		page_title='uuralur',
		page_icon='🤖',
		layout="wide",
		initial_sidebar_state="expanded",
	)

	sidebar()
	body()

if __name__ == '__main__':
	main()