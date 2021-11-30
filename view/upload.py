import os,datetime,yaml,hashlib
import streamlit as st
ss = st.session_state # global shorthand for this file
import parse
config = yaml.safe_load(open('data/config.yaml'))

def is_file_dupl(path,data):
	new_hash = hashlib.md5(data).hexdigest()
	for filename in os.listdir(path):
		if os.path.isfile(path+filename):
			filehash = hashlib.md5(open(path+filename,'rb').read()).hexdigest()
			if filehash == new_hash:
				return filename
	return False


def main():
	st.header('uploads')
	st.markdown("""
		You can upload matches in the `.cohdemo` file format here. 
		Record these ingame with the `/demorecord <file name here>` slash command. 
		Stop recording with the `/demostop` command or automatically when you exit the match.
		Saved files are found in the `<coh install path>\\demos` folder.

		Uploads are not visible from the sidebar navigator and are only accessible from the link generated from parsing here (so remember the link).
		Uploaded matches are not included in *records* stats.
		Uploaded matches and their links may be deleted or overwritten at some point. 
		Matches uploaded may be added to the main database at a later date.

		All uploads from the same date are shared within the same series.
		The program will attempt to check for duplicate files, otherwise and reuploads of matches will not overwrite the old match.
		Demos of the same match from multiple pov's will not be flagged as duplicate files.	
		File names are not preserved when uploading. 

		There is a daily limit to number of uploads to manage storage space, so don't mass-upload demos.
		Contact Xhiggy if you'd like to add a large amount of demos to the site.
		Invalid demos will likely result in an error or incorrect parsed data (team sizes too small, more than 2 teams, etc.)

		""")

	upload_st = st.empty()
	uploaded_file = upload_st.file_uploader('upload ".cohdemo" file', type='.cohdemo', accept_multiple_files=False, key=None, help=None, on_change=None, args=None, kwargs=None)
	if uploaded_file is not None:
		# format date for folder name
		f_date = str(datetime.date.today()).replace('-','')[2:]
		f_sid = f_date + "_upload"

		# f_name = uploaded_file.name
		bytes_data = uploaded_file.getvalue()

		demo_matches = ['Version','maps/Arena','Time']
		check_valid  = all(match in str(bytes_data[0:500]) for match in demo_matches)
		if not check_valid:
			st.error('Demo cannot be read by parser')
		else:

			f_path = "publicdemos/" + f_sid +"/"
			parsepath = f_path
			parseflag = 'm' # parse as match if series exists in db
			if not os.path.exists(f_path): # if new folder/series
				os.makedirs(f_path)
			folder_size = len(os.listdir(f_path))# number of files in folder
			if folder_size < config['daily_upload_limit']: # so storage can't get overrun
				
				# save upload
				list_fnames = [x.replace('.cohdemo','') for x in os.listdir(f_path)]
				list_fnames = [int(x.replace('.cohdemo','')) for x in list_fnames if x.isnumeric()]
				if list_fnames:
					f_mid = str(max(list_fnames)+1)
				else:
					f_mid = 1
				f_name = str(f_mid) + ".cohdemo" # demo name by number in folder

				sid = f_sid
				mid = f_mid

				def go_to_match():
					ss.view = {'match':'summary'}
					ss.sid = sid
					ss.mid = mid
					ss.new_mid = True

					ss['app_choice'] = 'players'

					params = st.experimental_get_query_params()
					params['s'] = sid
					params['m'] = mid
					st.experimental_set_query_params(**params) 


				with st.spinner('checking for duplicates of file'):
					dup_check = is_file_dupl(f_path,bytes_data)
				if dup_check:
					mid = dup_check.replace('.cohdemo','')
					st.warning('Demo appears to already exist in uploads')
					st.button('click here to view',on_click=go_to_match)
				else:
					f = open(f_path+f_name, "wb")
					f.write(bytes_data)
					f.close()
					print("{} saved".format(uploaded_file))
					# os.system("parse.py -m {} -d publicdemos.db".format(f_path + f_name))
					with st.spinner('attemping to read demo...'):
						try:
							if len(os.listdir(f_path)) == 0:
								parseflag = 's' # parse for series entry if no uploads exist
							if parseflag == 'm':
								parsepath += f_name
							parse.main(['-'+parseflag,parsepath])

							st.success('Demo parsed successfully')
							st.button('click here to view',on_click=go_to_match)
							st.caption('(remember the link to access)')
						except:
							st.error('Problem reading demo file.')
							os.remove(f_path+f_name) # delete the demo if it couldn't be read

			else:
				st.error('Uploads over limit for the day. Try again later.')