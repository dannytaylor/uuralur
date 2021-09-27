#!/usr/bin/env python

# streamlist tutorial test/placeholder
import os, sys, time, math, argparse, json, datetime, yaml, base64

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import numpy as np

# for displaying icons
from PIL import Image
from io import BytesIO
from IPython.core.display import HTML

# sqlite connections
con = sqlite3.connect('demos.db')
# con = sqlite3.connect('publicdemos.db')
cur = con.cursor()

# global vars/config
config = yaml.safe_load(open('data/config.yaml'))
h2p = json.loads(open('data/hero2player.json').read())
query_params = st.experimental_get_query_params()


def getdbdata(table,columns=None,conditions=None):
	if not columns and not conditions:
		cur.execute('''SELECT * FROM '''+table)
	elif columns or conditions:
		sql = "SELECT * FROM " + table
		if columns:
			cols = columns[0]
			for i in range(1,len(columns)):
				cols += ','+columns[i]
			sql = "SELECT "+ cols + " FROM " + table
		if conditions:
			sql += " WHERE " + conditions
		cur.execute(sql)
	data = cur.fetchall()


	return data

def path_to_image_html(path):
	return '<img src=http://localhost:8000/assets/icons/powers/'+ path + ' width="32" >'

# https://www.kaggle.com/stassl/displaying-inline-images-in-pandas-dataframe
# format images as base64 to get around streamlit static content limitations
def image_base64(path):
	path = 'assets/icons/powers/' + path
	im = Image.open(path)
	with BytesIO() as buffer:
		im.save(buffer, 'png')
		return base64.b64encode(buffer.getvalue()).decode()
def image_formatter(path):
	return f'<img src="data:image/jpeg;base64,{image_base64(path)}">'

def sidebar():
	st.sidebar.header('uuralur🪞')
	seriesdata = getdbdata('series')
	matchdata = []

	seriescontainer = st.sidebar.container()
	matchescontainer = st.sidebar.container()
	settingscontainer = st.sidebar.container()

	seriesselect = seriescontainer.empty()
	seriesdates = seriescontainer.expander('filter series dates')
	with seriesdates:
		date1=st.date_input('start date',datetime.date.fromisoformat('2020-07-15'),datetime.date.fromisoformat('2020-07-15'))
		date2=st.date_input('end date',min_value=datetime.date.fromisoformat('2020-07-15'))
		serieslist = [s[0] for s in seriesdata if (datetime.date.fromisoformat(s[1]) >= date1 and datetime.date.fromisoformat(s[1]) <= date2)]
		serieslist.reverse()
	seriesids = seriesselect.multiselect('series', serieslist)

	if seriesids:
		matchdata = getdbdata('matches',conditions=('series_id IN ' + str(seriesids).replace('[','(').replace(']',')')))
	

	matchids = []
	if len(seriesids) == 1:
		matchliststr = [str(m[0]) + " (" + m[2] + ")" for m in matchdata if m[1]==seriesids[0]]
		matchids = matchescontainer.multiselect('matches', matchliststr)
		matchids = [int(m.split(' ')[0]) for m in matchids]


	settings = settingscontainer.expander('settings',expanded=False)
	settingsform = settings.form('settingsform')
	with settings:
		global toggle_filter
		global pname_toggle
		global toggle_only_spike
		toggle_filter = settingsform.checkbox('filter toggles', value=True,help='filters out misc. toggles from actions by default. e.g. fly, armour toggles')
		pname_toggle = settingsform.checkbox('toggle player names', value=True,help='use playernames instead of hero names where available. e.g. change ghostmaster to xhiggy')
		toggle_only_spike = settingsform.checkbox('toggle only spike actions', value=True,help='toggles to show other powers during spike window in spike log')
		
		settings_save = settingsform.form_submit_button(label='save', help=None, on_click=None)


	return seriesids,matchids,matchdata


def main():
	st.set_page_config(
		page_title='uuralur',
		page_icon='🤖',
		layout="wide",
		initial_sidebar_state="expanded",
	)

	sid,mid,matchdata = sidebar()

	col1,col2,col3,col4 = st.columns([1,1,4,4])

	actioncontainer = col4.container()
	if len(sid) == 1:
		sid = sid[0]
		if len(mid) == 1:
			mid = mid[0]
			matchdata = [m for m in matchdata if m[0] == mid][0]
			if matchdata:
				col1.metric("blue score",matchdata[4],matchdata[4]-matchdata[5])
				col2.metric("red score",matchdata[5],matchdata[5]-matchdata[4])
				col1.metric("blue spikes",matchdata[6],matchdata[6]-matchdata[7])
				col2.metric("red spikes",matchdata[7],matchdata[7]-matchdata[6])


			with col4:
				spikedata = getdbdata('spikes',conditions=('series_id=\'' + str(sid) + '\' AND match_id=\'' + str(mid) + '\''))
				
				spikefilters = col4.expander('spike filters')
				spikeform = spikefilters.form('spike filter form')
				spike_heroes = {h[5] for h in spikedata}
				spf_heroes = spikeform.multiselect('heroes',spike_heroes)
				spikeform.form_submit_button(label='apply filters', help=None, on_click=None)

				spikeliststr = [datetime.datetime.fromtimestamp(s[3]/1000).strftime('%M:%S') +  "  [" + str(s[0]) + "]  " + s[5] for s in spikedata]
				if spf_heroes:
					spikeliststr = [datetime.datetime.fromtimestamp(s[3]/1000).strftime('%M:%S') +  "  [" + str(s[0]) + "]  " + s[5] for s in spikedata if (s[5] in spf_heroes)]

				spikeid = col4.selectbox('spikes', spikeliststr)
				spikeid = int(spikeid.split('[')[-1].split(']')[0])


				# columns = "substr(strftime(\'%M:%f\', time_ms/1000.0, \'unixepoch\'),0,9) as action_time ,actor,action,target"

				if spikeid:
					spikestart = spikedata[spikeid-1][3]
					spikeend   = spikedata[spikeid-1][4]+spikestart

					# spike sql query
					columns = "icon,time_ms,actor,action,target,hit_time,hit_hp"
					table = "actions"
					conditions = "series_id=\'" + str(sid) + "\' AND match_id=\'" + str(mid) + '\''
					conditions += " AND time_ms>= " + str(spikestart - config['spike_display_extend'])
					conditions += " AND time_ms<= " + str(spikeend + config['spike_display_extend'])
					if toggle_filter:
						conditions +=  " AND (action_type <> 'Toggle' OR action_target_type <> 'Self')"
						# conditions +=  " OR (action_target_type IS NULL))" # add to include KB/deaths in filter
					if toggle_only_spike:
						conditions +=  " AND spike_id=" + str(spikeid)
					sqlq = "SELECT " + columns + " FROM " + table + " WHERE " + conditions
					df = pd.read_sql_query(sqlq, con)

					# hp sql query
					columns = "time_ms,hp,hp_loss"
					table = "hp"
					conditions = "series_id=\'" + str(sid) + "\' AND match_id=\'" + str(mid) + '\''
					conditions += " AND hero=\'"+spikedata[spikeid-1][5] + "\'"
					conditions += " AND time_ms>= " + str(spikestart - config['spike_display_extend'])
					conditions += " AND time_ms<= " + str(spikeend + config['spike_display_extend'])
					sqlq = "SELECT " + columns + " FROM " + table + " WHERE " + conditions
					hpdf = pd.read_sql_query(sqlq, con)

					# hp graph data
					hpdf['spike_time'] = (hpdf['time_ms']-spikestart)/1000 # convert to relative time
					hpdf.at[0,'hp_loss'] = 0 # start at 0 HP loss
					hpdf['hp_loss'] = hpdf['hp_loss'].cumsum() # convert hp loss @ time to cumulative
					if spikedata[spikeid-1][8]:
						deathatrow = len(hpdf)
						for i in range(len(hpdf['hp'])):
							if hpdf['hp'][i] == 0:
								deathatrow = i+1
								break
						hpdf = hpdf[0:deathatrow]
					hpfig = px.line(hpdf, x="spike_time", y=["hp","hp_loss"])
					hpfig.update_layout(
						# title={'text':'HP and HP losses on spike'},
						height=360,
						# showlegend=False,
						legend_title='',
						plot_bgcolor='white',
						xaxis_title="time (s)",
						yaxis={'visible': False, 'showticklabels': False,'fixedrange':True},
						xaxis={'fixedrange':True}
					)
					
					
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
					for i in range(len(df['icon'])):
						df.at[i,'icon'] = image_formatter(df['icon'][i])
					df.sort_values(by='time_ms')
					df = df.assign(hack='').set_index('hack')
					df = df.style.format({"time_ms": "{:.2f}"})
					df = df.to_html()
					
					col4.write(df,unsafe_allow_html=True)
					col4.plotly_chart(hpfig, use_container_width=True)
					# col4.write(df,height=640)




if __name__ == '__main__':
	main()