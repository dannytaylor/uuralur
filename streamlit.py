#!/usr/bin/env python

# streamlist tutorial test/placeholder
import os, sys, time, math, argparse, json

from datetime import date
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import numpy as np

# sqlite connections
con = sqlite3.connect('demos.db')
# con = sqlite3.connect('publicdemos.db')
cur = con.cursor()

# global vars


def getdbdata(table,columns=None,conditions=None):
	if not columns and not conditions:
		cur.execute('''SELECT * FROM '''+table)
	elif columns and conditions:
		cols = columns[0]
		for i in range(1,len(columns)):
			cols += ','+columns[i]
		sql = "SELECT "+ cols + " FROM " + table + " WHERE " + conditions
		cur.execute(sql)

	data = cur.fetchall()
	return data

def sidebar():
	st.sidebar.header('uuralur🪞')
	seriesdata = getdbdata('series')
	matchdata = getdbdata('matches')

	seriescontainer = st.sidebar.container()

	with st.sidebar.expander('filter series dates'):
		date1=st.date_input('start date',date.fromisoformat('2020-07-15'),date.fromisoformat('2020-07-15'))
		date2=st.date_input('end date',min_value=date.fromisoformat('2020-07-15'))
		serieslist = [s[0] for s in seriesdata if (date.fromisoformat(s[1]) >= date1 and date.fromisoformat(s[1]) <= date2)]
		serieslist.reverse()
	
	seriesids = seriescontainer.multiselect('series', serieslist)

	matchescontainer = st.sidebar.container()
	matchids = []
	if len(seriesids) == 1:
		matchliststr = [str(m[0]) + " (" + m[2] + ")" for m in matchdata if m[1]==seriesids[0]]
		matchids = matchescontainer.multiselect('matches', matchliststr)
		matchids = [int(m.split(' ')[0]) for m in matchids]
	return seriesids,matchids


def main():
	st.set_page_config(
		page_title='uuralur',
		page_icon='🤖',
		layout="wide",
		initial_sidebar_state="expanded",
	)

	sid,mid = sidebar()

	actioncontainer = st.container()
	if len(mid) == 1 and len(sid) == 1:
		sid,mid = sid[0],mid[0]
		actiondata = getdbdata('actions',columns=['action_time','actor','action','target'],conditions=('series_id=\'' + str(sid) + '\' AND match_id=\'' + str(mid) + '\''))
		st.dataframe(actiondata)


	
	with st.expander('expando', expanded=True):
		st.subheader('test')
		# if matchidparam:
		# 	st.subheader(matchidparam)


if __name__ == '__main__':
	main()