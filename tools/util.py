# for displaying icons
from PIL import Image
from io import BytesIO
import base64
import streamlit as st

@st.cache
def str_sqlq(table,sid=None,mid=None,columns='*',conditions=None):
	where = ""
	if sid: 
		where += " WHERE " + "series_id='" + str(sid) + "'"
		if mid:
			where += " AND match_id='" + str(mid) + "'"
		if conditions:
			where += conditions
	return "SELECT " + ','.join(columns) + " FROM " + table + where


# https://www.kaggle.com/stassl/displaying-inline-images-in-pandas-dataframe
# format images as base64 to get around streamlit static content limitations
@st.cache
def image_base64(path):
	path = 'assets/icons/' + path
	im = Image.open(path)
	with BytesIO() as buffer:
		im.save(buffer, 'png')
		return base64.b64encode(buffer.getvalue()).decode()
@st.cache
def image_formatter(path):
	return f'<img src="data:image/jpeg;base64,{image_base64(path)}">'

# from https://discuss.streamlit.io/t/bug-weird-behavior-in-multipage-apps-with-query-params/17524
class MultiView:
	def __init__(self):
		self.apps = []
		self.app_names = []

	def add_app(self, title, func, *args, **kwargs):
		self.app_names.append(title)
		self.apps.append({
			"title": title,
			"function": func,
			"args":args,
			"kwargs": kwargs
		})

	def run(self, label='Go To'):
		# common key
		key='Navigation'

		# get app choice from query_params
		query_params = st.experimental_get_query_params()
		query_app_choice = query_params['app'][0] if 'app' in query_params else None

		# update session state (this also sets the default radio button selection as it shares the key!)
		st.session_state[key] = query_app_choice if query_app_choice in self.app_names else self.app_names[0]

		# callback to update query param from app choice
		def on_change():
			params = st.experimental_get_query_params()
			params['app'] = st.session_state[key]
			st.experimental_set_query_params(**params)
		app_choice = st.sidebar.radio(label, self.app_names, on_change=on_change, key=key)

		# run the selected app
		app = self.apps[self.app_names.index(app_choice)]
		app['function'](app['title'], *app['args'], **app['kwargs'])
