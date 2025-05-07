# app.py
from hydralit import HydraApp
from apps.about import AboutApp
from apps.video_reviewer import VRApp
from apps.home import HomeApp

app = HydraApp(title="Grappling Platform", hide_streamlit_markers=True, use_navbar=True, navbar_sticky=True, navbar_theme = {'menu_background':'orange'})

app.add_app("🏠 Dashboard", app=HomeApp())
app.add_app("🎞️ Video Review", app=VRApp())
app.add_app("ℹ️ About", app=AboutApp())
app.run()

