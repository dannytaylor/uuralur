# for displaying icons
from PIL import Image
from io import BytesIO
import base64
import streamlit as st

@st.cache
def str_sqlq(table,sid=None,mid=None,columns='*',conditions=None):
	where = ""
	if sid: 
		where += " WHERE " + "series_id='" + str(sid) 
		if mid:
			where += "' AND match_id='" + str(mid) + "'"
		if conditions:
			where += conditions
	return "SELECT " + ','.join(columns) + " FROM " + table + where


# https://www.kaggle.com/stassl/displaying-inline-images-in-pandas-dataframe
# format images as base64 to get around streamlit static content limitations
@st.cache
def image_base64(path):
	path = 'assets/icons/powers/' + path
	im = Image.open(path)
	with BytesIO() as buffer:
		im.save(buffer, 'png')
		return base64.b64encode(buffer.getvalue()).decode()
def image_formatter(path):
	return f'<img src="data:image/jpeg;base64,{image_base64(path)}">'

def set_view_mode(sid,mid):
	if len(mid) == 1:
		return 'match'
	elif len(sid) == 1:
		return 'series'
	else:
		return False