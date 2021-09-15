# streamlist tutorial test/placeholder

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import time

def main():
	df = pd.read_csv("data/1.cohdemo.csv", index_col=0).reset_index(drop=True)

	args = st.experimental_get_query_params()
	
	try:
		matchidparam = args['matchid'][0]
	except:
		matchidparam = False	


	st.set_page_config(
		page_title='demo data',
		page_icon='🤖',
		layout="wide",
		initial_sidebar_state="expanded",
	)

	st.sidebar.header('demoparse')
	raw = st.sidebar.checkbox('Show raw data')

	if raw:
		st.subheader('Raw data')
		
		all_players = df.player.unique().tolist()
		player_filter = st.multiselect("Players", all_players, default=all_players)

		dfsummary = df[df['linetype']=='summary_stats']
		st.write(df[df.player.isin(player_filter)])
		st.write(df.describe())
		st.write(dfsummary)
		st.dataframe(dfsummary[["player","team"]],height=800)

	# For univariate distributions
	# histogram to better understand
	with st.expander('expando', expanded=True):
		st.subheader('test')
		if matchidparam:
			st.subheader(matchidparam)

	st.header("Histogram")
	hist_x = st.selectbox("Histogram variable", options=df.columns, index=df.columns.get_loc("targeted"))
	hist_bins = st.slider(label="Histogram bins", min_value=5, max_value=50, value=25, step=1)
	hist_cats = df[hist_x].sort_values().unique()
	hist_fig = px.histogram(df, x=hist_x, nbins=hist_bins, title="Histogram of " + hist_x,
							template="plotly_white", category_orders={hist_x: hist_cats})
	st.write(hist_fig)

	st.multiselect('Multiselect', [1,2,3])


if __name__ == '__main__':
	main()