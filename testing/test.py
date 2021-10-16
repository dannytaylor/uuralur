import streamlit as st

class MultiPage:
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

def app1(title, info=None):
    st.title(title)
    st.write(info)
def app2(title, info=None):
    st.title(title)
    st.write(info)
def app3(title, info=None):
    st.title(title)
    st.write(info)

mp = MultiPage()
mp.add_app('Application 1', app1, info='Hello from App 1')
mp.add_app('Application 2', app2, info='Hello from App 2')
mp.add_app('Application 3', app3, info='Hello from App 3')
mp.run('Launch application')