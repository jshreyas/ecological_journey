# apps/about.py
import streamlit as st # type: ignore
from hydralit import HydraHeadApp # type: ignore


class AboutApp(HydraHeadApp):

    def run(self):

        st.title("🥋 About This Platform")

        st.markdown("""
        ### Empowering the Martial Artist
        This platform is an open-source ecosystem for martial artists to **track**, **vlog**, and **share** their training journeys. 
        Whether you're a beginner rolling your first rounds, a capoeirista exploring the flow, or a cross-discipline athlete, this space is yours.

        We believe in **empowering students** to own their journey, reflect with confidence, and build a **living portfolio** of their evolving skills. 

        Think of this as **GitHub meets Strava for martial artists** — but with the soul of a dojo.
        """)

        st.divider()

        st.markdown("""
        ### 🧠 Inspiration
        This project was born out of two needs:

        1. **Personal insight** — As martial artists, we often forget how far we've come. This tool helps you **see the arc** of your own growth.
        2. **Community learning** — Training isn’t just about what you learn from the coach — it's about **what we teach each other**, by playing, failing, and reflecting.

        It’s also a love letter to all the late-night YouTube video breakdowns, the after-class chats, the sparring sessions that changed our game, and the feeling of being part of something **bigger than ourselves**.
        """)

        st.divider()

        st.markdown("""
        ### 🧘‍♂️ Philosophy
        Martial arts isn’t just combat — it’s a way of **being**.

        We see martial arts as a **living ecosystem** of body, mind, and community. This platform exists to:

        - Help you build an **intentional practice**
        - Support **cross-training and open learning**
        - Celebrate not just results, but **process and progression**
        - Create a sense of **ritual and reflection**, the way ancient martial traditions did

        This is a space for **students of movement**. For those who flow between disciplines. For those who want to leave a trail behind — not just for themselves, but for the next traveler.

        We train. We log. We grow. Together.
        """)

        st.info("Open source. Forever free. Forever yours.")
