import os, sys, time, math, argparse, json, datetime, yaml, sqlite3

import streamlit as st
ss = st.session_state # global shorthand for this file

import pandas as pd
import numpy as np
import tools.util as util

import plotly.express as px
import plotly.graph_objects as go

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# sqlite connections
con = sqlite3.connect('demos.db')
cur = con.cursor()

# global vars/config
config = yaml.safe_load(open('data/config.yaml'))
h2p    = json.loads(open('data/hero2player.json').read())

# setup global vars for st
if "sid" not in ss: ss.sid = []
if "mid" not in ss: ss.mid = []
if "view" not in ss: ss.view = None

# setup series/match multiselect dataframes
if 'series' not in ss:	
	ss.series 		= pd.read_sql_query("SELECT * FROM Series", con)
	ss.series['date'] = pd.to_datetime(ss.series['series_date'])
	ss.series['date'] = ss.series['date'].dt.date
if 'matches' not in ss:
	ss.matches 			= pd.read_sql_query("SELECT * FROM Matches", con)



# filter series by settings
def series_filters():
	dates_expander = st.sidebar.expander('filters',expanded=False)
	series_filters = {}
	with dates_expander:
		dates = ss.series['date'].tolist()
		series_filters['date_first'] = st.date_input('start date filter',value=dates[0],min_value=dates[0],max_value=dates[-1])
		series_filters['date_last']  = st.date_input('end date filter', value=dates[-1],min_value=series_filters['date_first'] ,max_value=dates[-1])
		series_filters['kickball']   = st.checkbox('kickball',	  value=True,help="Any kickball/community series")
		series_filters['scrims']     = st.checkbox('scrims', value=True,help="Any non-KB, typically set team versus team")
	series_filtered = ss.series[(ss.series['date'] >= series_filters['date_first']) & (ss.series['date'] <= series_filters['date_last'])]

	# filter series by series type
	if not series_filters['kickball'] and series_filters['scrims']:
		series_filtered = series_filtered[series_filtered['kb'] == 0]
	if series_filters['kickball'] and not series_filters['scrims']:
		series_filtered = series_filtered[series_filtered['kb'] == 1]

	return series_filtered



def sidebar():
	st.sidebar.header('uuralur')

	with st.sidebar.container():
		ss.view = {st.radio('view mode',['match','series','players']):None}
	
	pickers = st.sidebar.container()

	navigator = st.sidebar.container()

	sid_filtered = series_filters() # filter series for selecting by options
	sid_filtered = sid_filtered['series_id'].to_list()
	sid_filtered.reverse()
	

	# only show MID picker if single SID selected
	if 'match' in ss.view or 'series' in ss.view:
		ss.sid = pickers.selectbox("series",sid_filtered)

		if 'match' in ss.view:
			sid_matches = ss.matches[ss.matches['series_id'] == ss.sid] # update match list for SID only

			# format text to display map name in multiselect
			sid_mids = sid_matches['match_id']
			
			sid_matches = sid_matches.set_index('match_id') # update match list for SID only
			def format_mid_str(mid):
				return str(mid) + " (" + sid_matches.loc[mid,'map'] + ")"
			
			ss.mid = pickers.selectbox("match",sid_mids,format_func=format_mid_str) 

	with navigator:
		if 'match' in ss.view:
			ss.view['match'] = st.radio('navigation',['summary','spikes','offence','defence','support','logs'])


def body():

	st.markdown(
				f"""
		<style>
			.reportview-container .main .block-container{{
				max-width: 1560px;
				padding-top: 1rem;
				padding-right: 1rem;
				padding-left: 1rem;
				padding-bottom: 1rem;
			}}
			# .reportview-container .main {{
			#     color: blue;
			# }}
		</style>
		""",
				unsafe_allow_html=True,
	)
	if 'match' in ss.view:
		# high level score,map,etc. to go hero
		
		sqlq = util.str_sqlq('Heroes',ss.sid,ss.mid)
		hero_df = pd.read_sql_query(sqlq, con)
		hero_list = hero_df['hero'].tolist()

		sqlq = util.str_sqlq('Actions',ss.sid,ss.mid)
		actions_df = pd.read_sql_query(sqlq, con)
		actions_df['time'] = pd.to_datetime(actions_df['time_ms'],unit='ms').dt.strftime('%M:%S.%f').str[:-4]


		# START SUMMARY PAGE
		if ss.view['match'] == 'summary':
			st.header('summary')

			c1,c2 = st.columns([1,2])
			hdf = hero_df[['hero','team','archetype','set1','set2','deaths','targets']].copy()

			with c2:
				teammap = {0:'🔵',1:'🔴'}
				hdf = hdf.sort_values(by='team')
				hdf['team'] = hdf['team'].map(teammap)
				hdf = hdf.set_index(['hero'])
				st.dataframe(hdf.style.format(na_rep='-'),height=520)
		# END SUMMARY PAGE


		# START SPIKES
		elif ss.view['match'] == 'spikes':
			st.header('spikes')

			c1,c2,c3,c4,c5,c6,c7,c8,c9,c10 = st.columns(10)
			c1.metric("test",1)
			c2.metric("test",1)
			c3.metric("test",1)

			c1,c2 = st.columns(2)

			# left side
			with c1:
				st.subheader('spike list')
				# get spike data for match
				sqlq = util.str_sqlq('Spikes',ss.sid,ss.mid,columns=['spike_id','time_ms','spike_duration','target','target_team','spike_hp_loss','kill'])
				
				## caching attempt to speed up
				# @st.cache(hash_funcs={sqlite3.Connection: id})
				# def return_df(sqlq,con):
				# 	return pd.read_sql_query(sqlq, con)
				# df = return_df(sqlq, con)
				
				df = pd.read_sql_query(sqlq, con)
				df = df.rename(columns={"spike_duration": "dur", "spike_id": "#","spike_hp_loss": "dmg","target_team": "team"})
				df['time'] = pd.to_datetime(df['time_ms'],unit='ms').dt.strftime('%M:%S')

				# select individual spikes
				st_spikes = st.empty()

				# spike filters
				filters = st.expander('spike filters',expanded=False)
				spike_filters = {}
				with filters:
					spike_filters['players'] = st.multiselect('heroes',hero_list)
					spike_filters['team'] = st.radio('team',['all','blue','red'])
					spike_filters['deaths'] = st.radio('deaths',['all','dead','alive'])
				sf = df.copy() # spikes filtered dataframe copy
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
				# spid = st_spikes.selectbox('select spike',sf,format_func=format_spike_str) # select from filtered
				
				
				# format data for printing table
				killmap = {None:'',1:'💀'}
				teammap = {'0':'🔵','1':'🔴'}
				sf['team'] = sf['team'].map(teammap)
				sf['kill'] = sf['kill'].map(killmap)
				sf['dur'] = sf['dur']/1000
				sf['dmg'] = sf['dmg'].astype(int)

				sf_write = sf[['#','time','team','target','dur','kill','dmg']]
				# sf_write = sf_write.set_index(['time','target'])	

				gb = GridOptionsBuilder.from_dataframe(sf_write)
				gb.configure_columns(['#','team','kill'],width=22)
				gb.configure_columns(['time','dur','dmg'],width=64)
				gb.configure_selection('single', pre_selected_rows=[0])
				gb.configure_columns('dur',type='customNumericFormat',precision=1)

				response = AgGrid(
					sf_write,
					gridOptions=gb.build(),
					# data_return_mode="filtered_and_sorted",
					update_mode='SELECTION_CHANGED',
					fit_columns_on_grid_load=True,
					height = 640,
					theme='material'
				)

				row = response['selected_rows']
				if row:
					spid = row[0]['#']
				else:
					spid = 1

				# st.dataframe(sf_write.style.format(precision=1,na_rep=' '),height=600)
 
				# for hp log
				sp_target   = df.loc[spid-1,'target'] # spiketarget
				sp_start = df['time_ms'][spid-1]
				sp_end   = df['dur'][spid-1]+sp_start

			# right side
			# spike log
			with c2:
				st.subheader('spike log')
				
				# spike hp log
				conditions = " AND hero=\'"+ sp_target.replace('\'','\'\'') + "\'"
				conditions += " AND time_ms>= " + str(sp_start - config['spike_display_extend'])
				conditions += " AND time_ms<= " + str(sp_end + config['spike_display_extend'])
				sqlq = util.str_sqlq('HP',ss.sid,ss.mid,['time_ms','hp','hp_loss'],conditions)
				hp_df = pd.read_sql_query(sqlq, con)

				# hp graph data
				hp_df['spike_time'] = (hp_df['time_ms']-sp_start)/1000 # convert to relative time
				hp_df.at[0,'hp_loss'] = 0 # start at 0 HP loss
				hp_df['hp_loss'] = hp_df['hp_loss'].cumsum() # convert hp loss @ time to cumulative
				if df.at[spid-1,'kill'] == 1: # if spike death truncate graph at death
					deathatrow = len(hp_df)
					for i in range(len(hp_df['hp'])):
						if hp_df['hp'][i] == 0:
							deathatrow = i+1
							break
					hp_df = hp_df[0:deathatrow]
				hpfig = px.line(hp_df, x="spike_time", y=["hp_loss","hp"],markers=False)
				hp_time = hp_df['spike_time'].tolist()
				hpfig.update_layout(
					height=320,
					showlegend=False,
					xaxis_title="spike time (s)",
					yaxis={'visible': True, 'showticklabels': False,'fixedrange':True},
					xaxis={'visible':True,'range':[min(0,hp_time[0]),hp_time[-1]]}
				)
				st.plotly_chart(hpfig, use_container_width=True)

				# grab actions with spike id
				sl = actions_df[(actions_df['spike_id'] == spid)] 
				# format spike dataframe
				sl = sl.rename(columns={"time": "match_time", "spike_time": "time", "spike_hit_time": "hit", "cast_dist": "dist"})
				sl['time'] = sl['time']/1000
				sl['hit'] = sl['hit']/1000
				sl['hit_hp'] = sl['hit_hp'].fillna(-1).astype(int).replace(-1,pd.NA)
				sl['dist'] = sl['dist'].fillna(-1).astype(int).replace(-1,pd.NA)
				# sl['image'] = '<image src=\'http:/localhost:8000/assets/icons/powers/' + sl['icon'] + '\'>'
				sl['icon_path'] = 'powers/'+sl['icon']
				sl['image'] = sl['icon_path'].apply(util.image_formatter)
				sl_write = sl[['time','actor','image','action','hit','dist','hit_hp']]	
				sl_write = sl_write.fillna('')



				## power icons in order as html, no aggrid
				# icons = sl['icon'][:]
				# icon_html = "<div style=\"text-align:center;\">"
				# for i in icons:
				# 	icon_html += util.image_formatter('powers/'+i) + "	"
				# icon_html += "<br><br></div>"
				# st.write(icon_html,unsafe_allow_html=True)

				# render html text as html
				icon_renderer = JsCode("""function(params) {
	                        return params.value ? params.value : '';
				}""")

				sl_gb = GridOptionsBuilder.from_dataframe(sl_write)
				sl_gb.configure_columns(['time','hit','hit_hp','dist'],width=96)
				sl_gb.configure_columns(['time','hit'],type='customNumericFormat',precision=2)
				sl_gb.configure_columns('image',cellRenderer=icon_renderer,width=64)

				sl_ag = AgGrid(
					sl_write,
					allow_unsafe_jscode=True,
					gridOptions=sl_gb.build(),
					fit_columns_on_grid_load=True,
					height = 640,
					theme='material'
				)

		# END SPIKES

def main():
	st.set_page_config(
		page_title='uuralur',
		page_icon='🤖',
		# layout="wide",
		initial_sidebar_state="expanded",
	)

	sidebar()
	body()

if __name__ == '__main__':
	main()