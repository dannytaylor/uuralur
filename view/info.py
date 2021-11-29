import yaml
import streamlit as st
ss = st.session_state # global shorthand for this file
config = yaml.safe_load(open('data/config.yaml'))



def main():
	st.caption('uuralur the mirror presides over the garden of [pvp] memories')
	st.subheader('General')
	st.write("""
		Demos shown on this website have been analyzed using a new parser (instead of *demoparse*) so numbers and stats may not match previously run stat programs. 
		The same general definitions, limitations, and methologies are the same. 
		Refer to the old Google Studio report definitions page for anything not covered on this page.
		""")
	st.write("""
		The intent with a new system was to make the data output from the demos more managable to use on a larger scale and in aggregate such as in this program. 
		The match viewer here is targeting parity with the old report system, plus some benefits from having more flexibility with the data and being able to have all matches in one place.
		""")


	st.subheader('Timing')
	st.write("""
		Timing is measured from a *spike start time* which is defined by the midpoint of the first 3 attacks within 1 second on a spike. 
		If a debuff is the first attack on a spike (EF, envenom), then it is the midpoint of the first 4 attacks within 2 seconds.
		""")


	st.subheader('On target')
	st.write("""
		Only half *on target* credit is given based on late timing of the first attack or heal on a target. 
		The previous version used some additional parameters to timing, but these thresholds provide a similar results and allow for standardizing metrics across multiple datasets and aligning with the old *demoparse*.
		""")
	st.write("""
		Attacks: If the first attack is cast more than {} milliseconds from the spike start time.
		""".format(str(config['otp_threshold'])))
	st.write("""
		Heals: If the first heal is cast more than {} milliseconds from the spike start time.
		""".format(str(config['ohp_threshold'])))