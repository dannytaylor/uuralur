import os,datetime,yaml,hashlib,time,re
import streamlit as st
ss = st.session_state # global shorthand for this file
import parse
config = yaml.safe_load(open('data/config.yaml'))

from tools.init_match import init_match

def is_file_dupl(path,data):
	new_hash = hashlib.md5(data).hexdigest()
	for filename in os.listdir(path):
		if os.path.isfile(path+filename):
			filehash = hashlib.md5(open(path+filename,'rb').read()).hexdigest()
			if filehash == new_hash:
				return filename
	return False


def main():
	st.header('📫 upload')
	st.markdown("""
		You can upload matches in the `.cohdemo` file format here. 
		Record these in-game with the `/demorecord <file name here>` slash command. 
		Stop recording with the `/demostop` command or automatically when you exit the match.
		Saved files are found in the `<coh install path>\\demos` folder.
		""")
		# If you would like a hero to count towards your global stats that isn't currently being tracked, fill out the form inputs in the sidebar.


	st.warning('Note this app was last significantly worked on in 2021 and may produce errors with recent demo files. \
		It does not include any data for new powersets released since and may confuse new instances of powers if they share animations or effects with other powers.',
		icon="⚠️")

	c1,c2=st.container(),st.container()
	upload_st = c1.empty()
	upload_sf = c2.empty()
	
	uploaded_file = upload_st.file_uploader('upload ".cohdemo" file', type='.cohdemo', accept_multiple_files=False)
	# upload_suffix = upload_sf.text_input('url suffix','',max_chars=2,help='alphanumeric only, leave blank for no suffix')
	# upload_suffix = re.sub(r'\W+', '', upload_suffix)

	# 240731 reenabled on request
	with st.sidebar.popover('📩 hero\:player addition'):
		with st.form('Enter both hero name and preferred global or alias below',clear_on_submit=True):
			heroname   = st.text_input("Hero Name", value="",help="Must be a valid CoH hero name. If it's a shared account with multiple users playing you may need to contact me to assign matches to the correct user.")
			playername = st.text_input("Alias or Global", value="",help="Enter your preferred alias to have your stats under. If your other heroes are already being tracked under a different alias use that name otherwise it may not be updated.")

			c0 = st.container()

			submitted = st.form_submit_button("submit")
			st.caption("This info is updated manually by me, so changes won't be immediate and may be modified before adding.")

			if submitted:
				if heroname == '' or playername == '':
					c0.warning("Fill in both fields.")
				else:
					submit_file = "data/player_names_submitted.txt"
					if os.path.getsize(submit_file) < 5000000: # quick file size limit to prevent it getting spammed
						with open(submit_file, "a") as myfile:
							submission_text = f"{datetime.date.today()} @{playername}:{heroname}\n"
							print("HERO SUBMISSION: ",submission_text) # print to console for easier reference
							myfile.write(submission_text)
							c0.success(f'{heroname}@{playername} submitted')

	if uploaded_file is not None:
		upload_sf.empty()
		# format date for folder name
		f_date = str(datetime.date.today()).replace('-','')[2:]
		# if upload_suffix:
		# 	upload_suffix = "_"+upload_suffix
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

					params = st.query_params.to_dict()
					params['s'] = sid
					params['m'] = mid
					st.query_params.from_dict({'s':params['s'],'m':params['m']})


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
					with st.spinner('attemping to read demo, may take > 1 minute if the site is under load'):
						try:
							parsepath += f_name
							print(sid,parsepath)
							os.system("python parse.py -m {} -i {}".format(parsepath,sid))

							time.sleep(2) # delay to ensure DB okay
							init_match(sid,int(mid),upload=True) # create cache pickle before first viewing

							time.sleep(0.5) 
							# parse.main(['-m',parsepath,'-i',sid])

							st.success('Demo parsed successfully')
							st.button('click here to view',on_click=go_to_match)
							st.caption('(remember the link to access)')
						except:
							st.error('Problem reading demo file.')
							os.remove(f_path+f_name) # delete the demo if it couldn't be read

			else:
				st.error('Uploads over limit for the day. Try again later.')
	with st.expander("upload notes", expanded=False):
		st.markdown("""
		Uploads are not visible from the sidebar navigator and are only accessible from the link generated from parsing here (so remember the link).
		Uploaded matches are not included in *records* stats.
		Uploaded matches and their links may be deleted or overwritten at some point. 
		Matches uploaded will typically be added to the main database at a later date.

		All uploads from the same date are shared within the same series.
		The program will attempt to check for duplicate files, otherwise and reuploads of matches will not overwrite the old match.
		Demos of the same match from multiple pov's will not be flagged as duplicate files.	
		File names are not preserved when uploading. 

		There is a daily limit to number of uploads to manage storage space, so don't mass-upload demos.
		Contact xhiggy if you'd like to add a large amount of demos to the site.
		Invalid demos will likely result in an error or incorrect parsed data (team sizes too small, more than 2 teams, etc.).
		Demo parsing may temporarily disable match viewing while demo is parsing (~10 seconds).

		""")