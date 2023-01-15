##### uuralur the mirror presides over the garden of pvp memories

record demos in game, arena maps only, with slash command  
`/demorecord DEMONAME`  
`/demostop` or stops on map exit  
demos saved to the `COH DIRECTORY\demos` location

dependencies  
``` pip install streamlit streamlit-aggrid plotly millify pandas numpy ujson```  

parse by main demo folder (all demos), by series, or a single match  
``` python parse.py -a PARENTFOLDERPATH | -s SERIESFOLDERPATH | -m MATCHDEMOPATH [-d DBFILE]```  
writes to demos.db by default

folder structure 
```
|- demos
    |- series 1
    |- series 2
        |- 1.cohdemo
        |- 2.cohdemo
        |- ...
    |- ...
```
recommend using the same naming convention as [me](https://demos.hcc.ovh/)

run web app with existing sqlite db  
``` streamlit run app.py```  

precache calculated match data in json  
``` python tools/init_match.py ```  
runs on all matches in db file without existing caches. delete cache file to force rerun on a match


