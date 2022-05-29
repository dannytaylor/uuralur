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

def resize_image(image_path,size):
	image = Image.open(image_path)
	image.thumbnail((size,size), Image.ANTIALIAS)
	return image

def hero_player_dict(h2p):
	h2p = {k: ("@"+v if v else k) for k, v in h2p.items()}
	dup_names = {}
	dup_names = {dup_names.setdefault(v, set()).add(k) for k, v in h2p.items()}
	n = 1
	for k in h2p:
		if h2p[k] in dup_names:
			h2p[k] = str(h2p[k]) + f" ({n})"
			n += 1
	h2p = {k: (v if v else k) for k, v in h2p.items()}
	return h2p

