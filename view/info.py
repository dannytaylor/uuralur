import yaml
import streamlit as st
ss = st.session_state # global shorthand for this file
config = yaml.safe_load(open('data/config.yaml'))


def main():
	st.image('assets/info_header.png')#,caption='uuralur the mirror presides over the garden of [pvp] memories')
	
	st.warning('Note this app is unmaintained since 2021 and may not work with changes to the game since.',
	icon="⚠️")

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
		Some limitations with the table formatting and framework used means everything is formatted for desktop computers only, 1280px wide minimum; sorry mobile viewers and small screens.
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
		[city of data](https://cod.uberguy.net./)  
		[this repo](https://github.com/dannytaylor/uuralur)  
		""")
	st.write("""
		Power data has been downloaded from CoD with some adjustments to work for this program. Some timing data may be wrong for weird edge-case powers.
		URLs generated when selecting matches can be shared to link to specific match.
		Heroes are mapped to players to the best of my knowledge. If you see a hero attributed to the wrong player I can fix it when I get a chance.
		The site is only designed for desktop viewing to work with the intended layouts and hacky solutions for the components used. Toggle mobile view in the sidebar for a partial workaround on phones. 
		Message me (xhiggy @forums, @discord, or @twitter) if you have any questions, or post in the [pvp resources thread](https://forums.homecomingservers.com/topic/15386-pvp-resources/) on the Homecoming forums.
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

	st.subheader('Legend')
	st.write('Terms and definitions used in the original 2020 parser and report copied below for reference. May not fully match current usage of terms.')
	with st.expander('Legend'):
		st.code("""
		SPIKES
		spike target - there's some additional parameters at play, but simplified: you need at least 2 people committing significant attacks on an enemy within a short spike timing window. e.g. 2 people blazing bolting an emp between targets won't get picked up, but 2 blazes at the same time will or 3 bb's at the same time will
		spike length - time from first attack to last attack on a spike
		kill length - time from first attack to target death
		cast time - start of a power cast in a demo file, typically when activated
		hit time - cast time plus + effect delay and estimated projectile travel time
		hit window - on a spike kill, the time between the first attack hit (excluding debuffs) and death
		cleanliness - average hit window

		OFFENCE
		primary attack - a non-trash damage attack. i.e. charged shot, ice blast would be considered trash, where as lancer shot or BIB would be considered primary (some wiggle room)
		on target - when a player fires at least 1 attack on an enemy who is determined a spike target
		late attack - if the first attack by a player on a spike at least 2 seconds after the start of the spike
		followup time - average time between starting first atk and second atk on a spike (for spikes with >1 atk)
		timing - average time in which you cast your first attack on a spike (from the first primary atk on the target)
		atk variance - variance of your timings
		k part (kill participation) - percent of successful spikes (kills) a player was on
		first - the first primary attack on an enemy determined a spike target, also determines the start of the spike
		first distance - average distance from target on first spike attacks
		first attack timing - bins first attacks on spike by timing relative to spike start


		DEFENCE/SUPPORT
		dmg/death - the average hp lost on lethal spikes, greater than your max HP means you're typically getting heals on spikes and still dying
		dmg/surv - the average hp lost on non-lethal spikes, you want this number to be less than your max HP - i.e. you want the typical spike on you to not require healing
		heals - the number of heal powers received
		non-spike dmg - total of all match hp losses that occurs while not a spike target
		greens - assumes a full tray of 20 was taken into the match
		jaunt reaction - avg time to cast jaunt after the start of a spike (prejaunts not counted)
		support
		heal speed (av spd) - heal cast time relative to the start of a spike (~reaction time)
		timing (avg tm) - absolute heal hit time relative to the first instance of damage (>100), i.e. practical heal timing. calc excludes spike targets starting below max HP or already taking damage.
		heal categories, all mutually exclusive and calculated in the following order:
		    early - heal that hits before any instance of damage taken on a full hp target
		    late - first heal on a target cast before but that lands after the target has died
		    quick - a first heal cast by <1.67s in of a spike or if it hits within <0.67s of first dmg
		    timely - cast or hit within twice of either the quick timing windows
		    slow - first on target heal slower than a timely heal (generally not a saving heal)
		    follow up - any heal on a spike target after a support's first heal on a spike target
		    top up - any heal cast on a teammate that is not being spiked and not at full hp (minus ff's)
		    fat finger (ff)  - top up heal on a full health teammate 
		alpha - a first (or tied first) heal on a spike target
		predict - if a spirit ward is cast within 12 seconds prior of a teammate becoming a spike target it counts as a predict (lasts for ~10s + projectile travel)
		phase heal - heals on a target who has already phased (i.e. uneffecting healing), estimated on from phase cast time
		heal efficacy - bins first heals cast by target missing HP at hit time
		late (quick) - late heals cast fast (<1.5 after spike start) to differentiate from 'reguar' late
		extras - includes some non-healing abilities done by a support (e.g. attacks, buffs, summons)
		cm - counts usage of cm-like powers (starting from after the buff period)


		OTHER
		rogue - any attack, phase, or green use outside of a spike window (entangles will show as strangler in the rogue log)
		gather - defined by an aoe buff hitting 4 or more teammates (outside of the buff period)
		utility power - generic term which includes some limited non-attack and non-heal powers, see source code for the list

		""",language=None)



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
	
	
	st.subheader(':)')

	# st.subheader('Definitions')
	# st.write("*Phase hit* - when a heal/attack is **cast** shortly after a phase power **finishes** activating.")
	# st.write("*Fat finger heal* - when a heal is cast on a player who is not the spike target who is full HP at **both** cast and hit time.")
	# st.write("* * - ")
	# 