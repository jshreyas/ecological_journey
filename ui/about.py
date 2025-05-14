from nicegui import ui

def about_page():
    with ui.column().classes('w-full max-w-4xl mx-auto p-6'):

        ui.label('🥋 About This Platform').classes('text-3xl font-bold mb-4')

        ui.markdown('''
        ### Empowering the Martial Artist

        This platform is an open-source ecosystem for martial artists to **track**, **vlog**, and **share** their training journeys.

        Whether you're a beginner rolling your first rounds, a capoeirista exploring the flow, or a cross-discipline athlete, this space is yours.

        We believe in **empowering students** to own their journey, reflect with confidence, and build a **living portfolio** of their evolving skills. 

        Think of this as **GitHub meets Strava for martial artists** — but with the soul of a dojo.
        ''')

        ui.separator()

        ui.markdown('''
        ### 🧠 Inspiration

        This project was born out of two needs:

        1. **Personal insight** — As martial artists, we often forget how far we've come. This tool helps you **see the arc** of your own growth.
        2. **Community learning** — Training isn’t just about what you learn from the coach — it's about **what we teach each other**, by playing, failing, and reflecting.

        It’s also a love letter to all the late-night YouTube video breakdowns, the after-class chats, the sparring sessions that changed our game, and the feeling of being part of something **bigger than ourselves**.
        ''')

        ui.separator()

        ui.markdown('''
        ### 🧘‍♂️ Philosophy

        Martial arts isn’t just combat — it’s a way of **being**.

        We see martial arts as a **living ecosystem** of body, mind, and community. This platform exists to:

        - Help you build an **intentional practice**
        - Support **cross-training and open learning**
        - Celebrate not just results, but **process and progression**
        - Create a sense of **ritual and reflection**, the way ancient martial traditions did

        This is a space for **students of movement**. For those who flow between disciplines. For those who want to leave a trail behind — not just for themselves, but for the next traveler.

        We train. We log. We grow. Together.
        ''')

        ui.label('💡 Open source. Forever free. Forever yours.') \
          .classes('bg-blue-100 text-blue-900 p-4 rounded shadow mt-4')
