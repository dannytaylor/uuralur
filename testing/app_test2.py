import os, sys, time, math, argparse, json, datetime, yaml, sqlite3
import tools.util
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder
import tools.util as util


# sqlite connections
con = sqlite3.connect('demos.db')
# public = sqlite3.connect('publicdemos.db')
cur = con.cursor()

# global vars/config
config = yaml.safe_load(open('data/config.yaml'))
h2p = json.loads(open('data/hero2player.json').read())

# st state state vars
if 'matches' not in st.session_state:	st.session_state.matches 	= pd.read_sql_query("SELECT * FROM Matches", con)
if 'series' not in st.session_state:	st.session_state.series 	= pd.read_sql_query("SELECT * FROM Series", con)

########
# sidebar, settings, and filters
########
def sidebar(sid,mid):
	st.sidebar.header('uuralur')

	series_container 		= st.sidebar.container()
	matches_container 		= st.sidebar.container()
	settings_container 		= st.sidebar.container()
	filter_map_container 	= st.sidebar.container()
	filter_series_container = st.sidebar.container()

	seriesselect = series_container.empty()
	date_filter = settings_container.expander('filter dates')
	ss_series = st.session_state.series
	ss_series['series_date'] = pd.to_datetime(ss_series['series_date'])
	ss_series['series_date'] = ss_series['series_date'].dt.date
	with date_filter:
		dates = ss_series['series_date'].tolist()
		dates.sort()
		d_min = dates[0]
		d_max = dates[-1]
		date_first = st.date_input('start date',value=d_min,min_value=d_min,max_value=d_max)
		date_last  = st.date_input('end date',value=d_max,min_value=d_min,max_value=d_max)
	series_filtered = ss_series[(ss_series['series_date'] >= date_first) & (ss_series['series_date'] <= date_last)]
	series_filtered = series_filtered['series_id'].to_list()
	query = st.experimental_get_query_params()
	series_query = None
	if 'series' in query and query['series'][0] in series_filtered:
		series_query = query['series']
	series_ids = seriesselect.multiselect('series', series_filtered,default=series_query)

	matches_filtered = pd.DataFrame()
	if series_ids:
		cond = "series_id IN " + str(series_ids).replace('[','(').replace(']',')')
		sqlq = util.strsqlquery('Matches',conditions=cond)
		matches_filtered = pd.read_sql_query(sqlq, con)

	

	match_ids = []
	match_query = None
	if not matches_filtered.empty:
		match_ids_filtered = matches_filtered['match_id'].to_list()
	if 'match' in query:
		if int(query['match'][0]) in match_ids_filtered:
			match_query = query['match'][0]
	if len(series_ids) == 1:
		match_str = matches_filtered['match_id'].astype(str) + ' (' +matches_filtered['map'] + ')'
		if match_query:
			match_query = match_query + " (" + matches_filtered.at[int(match_query)-1,'map'] + ")"
		match_ids = matches_container.multiselect('matches', match_str,default=match_query)
		match_ids = [int(m.split(' ')[0]) for m in match_ids]
		if len(match_ids) == 1:
			st.experimental_set_query_params(series=series_ids[0],match=match_ids[0])
		else:
			st.experimental_set_query_params(series=series_ids[0])


	settings = settings_container.expander('settings',expanded=False)
	settings_form = settings.form('settings_form')
	with settings:
		global toggle_filter
		global pname_toggle
		global toggle_only_spike
		toggle_filter = settings_form.checkbox('filter toggles', value=True,help='filters out misc. toggles from actions by default. e.g. fly, armour toggles')
		pname_toggle = settings_form.checkbox('toggle player names', value=True,help='use playernames instead of hero names where available. e.g. change ghostmaster to xhiggy')
		toggle_only_spike = settings_form.checkbox('toggle only spike actions', value=True,help='toggles to show other powers during spike window in spike log')
		
		settings_save = settings_form.form_submit_button(label='save', help=None, on_click=None)


	return series_ids,match_ids

def main_view(sid,mid):
	col1,col2 = st.columns([1,1])

	actioncontainer = col2.container()
	if len(sid) == 1:
		sid = sid[0]
		st.experimental_set_query_params(series=sid)
		if len(mid) == 1:
			st.experimental_set_query_params(series=sid,match=mid)
			mid = mid[0]
			
			cond = "series_id='" + str(sid) + "' AND match_id='" + str(mid) + "'"
			sqlq = util.strsqlquery('Matches',conditions=cond)
			match_data = pd.read_sql_query(sqlq, con)
			
			if 1:
				col1.header('match')
				col1.text('score   ' + str(match_data['score0'][0]) + " - " + str(match_data['score1'][0]))
				col1.text('spikes  ' + str(match_data['spikes0'][0]) + " - " + str(match_data['spikes1'][0]))

			with col1:
				# hero sql query
				st.header('heroes')
				columns = "hero,team,archetype,set1,deaths,targets,support"
				table = "heroes"
				conditions = "series_id=\'" + str(sid) + "\' AND match_id=\'" + str(mid) + '\''
				sqlq = "SELECT " + columns + " FROM " + table + " WHERE " + conditions
				hdf = pd.read_sql_query(sqlq, con)
				if pname_toggle:
					hdf['hero'] = hdf['hero'].map(h2p)
				
				col1.dataframe(hdf.style.hide_index().hide_columns(), height=600)

			with col2:
				col2.header('spikes')

				cond = "series_id=\'" + str(sid) + "\' AND match_id=\'" + str(mid) + '\''
				sqlq = util.strsqlquery('spikes',conditions=cond)
				spikedf = pd.read_sql_query(sqlq, con)

				killmap = {0:'',1:'💀'}
				spikedf['kill'] = spikedf['kill'].fillna(0).map(killmap)

				spikedf['time'] 		= pd.to_datetime(spikedf['time_ms'],unit='ms').dt.strftime('%M:%S')
				spikedf['duration'] 	= spikedf['spike_duration']/1000
							
				spike_ag = spikedf[['kill','time','target','duration']]
				gb = GridOptionsBuilder.from_dataframe(spike_ag)
				gb.configure_selection('single')
				AgGrid(spike_ag,
					    fit_columns_on_grid_load=True,
					    theme='material'
					)

				spikefilters = col2.expander('spike filters',expanded=False)
				spikeform = spikefilters.form('spike filter form')
				spike_heroes = {h for h in spikedf['target']}
				spf_heroes = spikeform.multiselect('heroes',spike_heroes)
				spikeform.form_submit_button(label='apply filters', help=None, on_click=None)

				spikedf['spikestr'] = spikedf['time'] + " [" + spikedf['spike_id'].astype(str) + "] " + spikedf['target']
				
				spikeid = col2.selectbox('spikes', spikedf['spikestr'] )
				spikeid = int(spikeid.split('[')[-1].split(']')[0])


				# columns = "substr(strftime(\'%M:%f\', time_ms/1000.0, \'unixepoch\'),0,9) as action_time ,actor,action,target"

				if spikeid:
					spikestart = spikedf['time_ms'][spikeid-1]
					spikeend   = spikedf['spike_duration'][spikeid-1]+spikestart

					# spike sql query
					columns = "time_ms,actor,action,target,hit_time,hit_hp,icon"
					table = "actions"
					conditions = "(series_id=\'" + str(sid) + "\' AND match_id=\'" + str(mid) + '\''
					conditions += " AND time_ms>= " + str(spikestart - config['spike_display_extend'])
					conditions += " AND time_ms<= " + str(spikeend + config['spike_display_extend']) + ")"
					if toggle_only_spike:
						conditions +=  " AND spike_id=" + str(spikeid)
					if toggle_filter:
						conditions +=  " AND NOT ((action_type = 'Toggle' and action_type IS NOT NULL)"
						conditions +=  " AND (action_target_type = 'Self' and action_target_type IS NOT NULL))"
					sqlq = "SELECT " + columns + " FROM " + table + " WHERE " + conditions
					df = pd.read_sql_query(sqlq, con)

					# hp sql query
					spike_target = spikedf['target'][spikeid-1].replace('\'','\'\'') # escape quote mark in name
					conditions = "series_id=\'" + str(sid) + "\' AND match_id=\'" + str(mid) + '\''
					conditions += " AND hero=\'"+ spike_target + "\'"
					conditions += " AND time_ms>= " + str(spikestart - config['spike_display_extend'])
					conditions += " AND time_ms<= " + str(spikeend + config['spike_display_extend'])
					sqlq = util.strsqlquery('hp',
										['time_ms','hp','hp_loss'],
										conditions)
					hpdf = pd.read_sql_query(sqlq, con)

					# hp graph data
					hpdf['spike_time'] = (hpdf['time_ms']-spikestart)/1000 # convert to relative time
					hpdf.at[0,'hp_loss'] = 0 # start at 0 HP loss
					hpdf['hp_loss'] = hpdf['hp_loss'].cumsum() # convert hp loss @ time to cumulative
					if spikedf.at[spikeid-1,'kill'] == '💀':
						deathatrow = len(hpdf)
						for i in range(len(hpdf['hp'])):
							if hpdf['hp'][i] == 0:
								deathatrow = i+1
								break
						hpdf = hpdf[0:deathatrow]
					hpfig = px.line(hpdf, x="spike_time", y=["hp_loss","hp"],markers=True)
					hpfig.update_layout(
						height=360,
						# showlegend=False,
						legend_title='',
						plot_bgcolor='rgba(0,0,0,0)',
						xaxis_title="time (s)",
						yaxis={'visible': False, 'showticklabels': False,'fixedrange':True},
						xaxis={'fixedrange':True}
					)
					
					icons = df['icon'][:]
					icon_path = 'assets/icons/powers/'
					icon_html = "<div style=\"text-align:center;\">"
					for i in icons:
						icon_html += util.image_formatter(i) + "	"
					icon_html += "</div>"

					df['time_ms'] = (df['time_ms']-spikestart)/1000
					df['hit_time'] = (df['hit_time']-spikestart)/1000
					df['hit_hp'] = df['hit_hp'].fillna(-1)
					df['hit_hp'] = df['hit_hp'].astype(int)
					df['hit_hp'] = df['hit_hp'].astype(str)
					df['hit_hp'] = df['hit_hp'].replace('-1','')
					if pname_toggle:
						df['actor'] = df['actor'].map(h2p)
						df['target'] = df['target'].map(h2p)
					df['target'] = df['target'].replace(pd.NA,'')

					# for i in range(len(df['icon'])):
					# 	df.at[i,'icon'] = image_formatter(df['icon'][i])

					df = df.drop(columns=['icon'])
					df = df.assign(hack='').set_index('hack')
					df = df.style.format({"time_ms": "{:.2f}","hit_time": "{:.2f}"})
					
					# df = df.to_html()
					# col2.write(df,unsafe_allow_html=True)

					col2.write('spike log')
					col2.dataframe(df,height=640)
					col2.write(icon_html,unsafe_allow_html=True)
					col2.plotly_chart(hpfig, use_container_width=True)
		else:
			st.experimental_set_query_params(series=sid)
	else:
		st.experimental_set_query_params()
	return

def get_query():
	sid,mid = None, None
	querys = st.experimental_get_query_params()
	if 'series' in querys:
		sid = querys['series']

	return sid,mid

def set_query(sid,mid):
	if sid:
		if mid:
			st.experimental_set_query_params(series=sid,match=mid)
		else:
			st.experimental_set_query_params(series=sid)
	return

def main():
	st.set_page_config(
		page_title='uuralur',
		page_icon='🤖',
		layout="wide",
		initial_sidebar_state="expanded",
	)

	sid,mid = get_query()

	sid,mid = sidebar(sid,mid)
	
	set_query(sid,mid)

	main_view(sid,mid)
	



if __name__ == '__main__':
	main()