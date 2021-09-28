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
# query_params = st.experimental_get_query_params()


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

def strsqlquery(table,columns,conditions):
	return "SELECT " + ','.join(columns) + " FROM " + table + " WHERE " + ','.join(conditions)

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
		matchliststr.sort()
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

	col1,col2 = st.columns([1,1])

	actioncontainer = col2.container()
	if len(sid) == 1:
		sid = sid[0]
		if len(mid) == 1:
			mid = mid[0]
			matchdata = [m for m in matchdata if m[0] == mid][0]
			if matchdata:
				col1.header('match')
				col1.text('score   ' + str(matchdata[4]) + " - " + str(matchdata[5]))
				col1.text('spikes  ' + str(matchdata[6]) + " - " + str(matchdata[7]))
				# col1.metric("blue score",matchdata[4],matchdata[4]-matchdata[5])
				# col1.metric("red score",matchdata[5],matchdata[5]-matchdata[4])
				# col1.metric("blue spikes",matchdata[6],matchdata[6]-matchdata[7])
				# col1.metric("red spikes",matchdata[7],matchdata[7]-matchdata[6])

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

				conditions = "(series_id=\'" + str(sid) + "\' AND match_id=\'" + str(mid) + '\')'
				sqlq = strsqlquery('spikes',['spike_id','time_ms','target','target_team','kill','spike_duration'],[conditions])
				spikedf = pd.read_sql_query(sqlq, con)

				for i in range(len(spikedf['time_ms'])):
					spikedf.at[i,'time'] = datetime.datetime.fromtimestamp(spikedf['time_ms'][i]/1000).strftime('%M:%S')
				spikedf['kill'] = spikedf['kill'].fillna(0)
				col2.dataframe(spikedf[['spike_id','time','target','kill']].style.format({"kill": "{:.0f}"}),height=200)


				spikedata = getdbdata('spikes',conditions=('series_id=\'' + str(sid) + '\' AND match_id=\'' + str(mid) + '\''))

				spikefilters = col2.expander('spike filters')
				spikeform = spikefilters.form('spike filter form')
				spike_heroes = {h for h in spikedf['target']}
				spf_heroes = spikeform.multiselect('heroes',spike_heroes)
				spikeform.form_submit_button(label='apply filters', help=None, on_click=None)

				spikeliststr = [datetime.datetime.fromtimestamp(s[3]/1000).strftime('%M:%S') +  "  [" + str(s[0]) + "]  " + s[5] for s in spikedata]
				if spf_heroes:
					spikeliststr = [datetime.datetime.fromtimestamp(s[3]/1000).strftime('%M:%S') +  "  [" + str(s[0]) + "]  " + s[5] for s in spikedata if (s[5] in spf_heroes)]

				spikeid = col2.selectbox('spikes', spikeliststr)
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
					conditions = "series_id=\'" + str(sid) + "\' AND match_id=\'" + str(mid) + '\''
					conditions += " AND hero=\'"+spikedf['target'][spikeid-1] + "\'"
					conditions += " AND time_ms>= " + str(spikestart - config['spike_display_extend'])
					conditions += " AND time_ms<= " + str(spikeend + config['spike_display_extend'])
					sqlq = strsqlquery('hp',
										['time_ms','hp','hp_loss'],
										[conditions])
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
						icon_html += image_formatter(i) + "	"
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




if __name__ == '__main__':
	main()