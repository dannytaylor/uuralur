# for displaying icons
from PIL import Image
from io import BytesIO
import base64


def strsqlquery(table,columns='*',conditions=None):
	where = ""
	if conditions: where = " WHERE " + conditions
	return "SELECT " + ','.join(columns) + " FROM " + table + where


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