import yaml
import streamlit as st
ss = st.session_state # global shorthand for this file
config = yaml.safe_load(open('data/config.yaml'))


def main():
	st.image('assets/info_header.png',caption='uuralur the mirror presides over the garden of [pvp] memories')
	st.subheader('Foreword')
	st.write("""
		This program is made for the standard structure of team arena matches: 8 vs 8, 10 minute area matches based around calling targets with multiple people attacking and healing characters on either team. 
		The further you deviate from the typical match structure (i.e. less than 6v6) the less useful this program becomes.
		This was made to provide a useful breakdown of matches and while it contains a lot of info about any given match, some of the details of how a match actually played out may not be obvious. 
		Some of the parameters in reporting are based around calibration of my own matches along side my vods as well as the old version of the parser.
		""")
	st.write("""
		Everything in these stats should be taken with a grain of salt as not all context can be or has been captured. 
		Looking at these stats plus vods from a couple different povs could give you the full picture, but hopefully this can save people some time for broad information.
		""")

	st.subheader('General')
	st.write("""
		Demos shown on this website have been analyzed using a new parser (instead of *demoparse*) so numbers and stats may not match previously run stat programs. 
		The same general definitions, limitations, and methologies are the same. 
		Refer to the old Google Studio report definitions and notes pages for anything not covered on this page.
		""")
	st.write("""
		The intent with a new system was to make the data output from the demos more managable to use on a larger scale and in aggregate such as in this program. 
		The match viewer here is targeting parity with the old report system, plus some benefits from having more flexibility with the data and being able to have all matches in one place.
		This site is a testing project with pieces put together as I learn about them generally without revisiting other pieces, so it's not the most optimized or clearly written, but also it's probably not getting changed much.
		""")
	st.markdown("""
		[old demoparse report](https://datastudio.google.com/u/1/reporting/dad5a39e-179a-49b4-ad64-a4f8ce89694e/page/hoC2B)  
		[old demoparse git repo](https://github.com/pvp-bot/demoparse)
		""")
	st.write("""
		Power data has been downloaded from CoD with some adjustments to work for this program. Some timing data may be wrong for weird edge-case powers.
		URLs generated when selecting matches can be shared to link to specific match.
		Heroes are mapped to players to the best of my knowledge. If you see a hero attributed to the wrong player I can fix it when I get a chance.
		The site is only designed for desktop viewing to work with the intended layouts and hacky solutions for the components used. Toggle mobile view in the sidebar for a partial workaround on phones. 
		Message me (xhiggy@forums, daniel#4509@discord) if you have any questions, or post in the [pvp resources thread](https://forums.homecomingservers.com/topic/15386-pvp-resources/) on the Homecoming forums.
		""")

	st.subheader('Demo limitations')
	st.write("""
		There are some limitations with coh demo record files where you may get some missing information from a match. 
		It will only record info within render range from your character (note this is different from perception range) so on larger maps you can miss some data, especially when you respawn far away from other players - this is usually the reason a parsed demo will have a different score from the match. 
		Some powers don't have effects, difficult to isolate effects, or share the same effects with other powers which makes some things difficult to account for. 
		Since spikes are based on certain actions in-game there will be a few false positives here and there but I've found the program to be pretty reliable in practice. 
		Damage and healing numbers are not included in demos, so some information needs to be calculated and/or estimated. 
		Absorb shields aren't included in demo files, so damage taken by absorbs do not count towards player HP loss.
		Player position and time at a position is not updated in the demo record regularly/consistently, so any distance reported between 2 players is a rough estimate based on available data.
		""")

	st.subheader('Timing/On Target')
	st.write("""
		Timing is measured from a *spike start time* which is defined by the midpoint of the first 3 attacks within 1 second on a spike. 
		If a debuff is the first attack on a spike (EF, envenom), then it is the midpoint of the first 4 attacks within 2 seconds.
		Average (mean) attack timing is measured by absolute value (so a < 0 timing attack will not necessarily bring the average down).
		All other mean calculations (heal, phase, jaunt) do not use an absolute value calculation.
		Note that this means these timings will appear slightly better than the old system in most situations.
		Median is probabably a better metric for general viewing in most cases.
		""")
	# st.subheader('On target')
	st.write("""
		Only half *on target* credit is given based on late timing of the first attack or heal on a target (relative to the spike start). 
		Calculations were adjusted to align with results from the old demoparse OTP calculations.
		""")

	# st.subheader('Definitions')
	# st.write("*Phase hit* - when a heal/attack is **cast** shortly after a phase power **finishes** activating.")
	# st.write("*Fat finger heal* - when a heal is cast on a player who is not the spike target who is full HP at **both** cast and hit time.")
	# st.write("* * - ")
	# 