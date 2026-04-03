import { loadResource } from "../../static/utils/resources.js";

export default {
  template: "<div></div>",
  props: {
    options: Array,
    resourcePath: String,
  },
  async mounted() {
    await this.$nextTick(); // NOTE: wait for window.path_prefix to be set
    await loadResource("https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js");
    this.options.eventClick = (info) => this.$emit("click", { info });
    this.calendar = new FullCalendar.Calendar(this.$el, this.options);
    this.calendar.render();
  },
  methods: {
    update_calendar() {
      if (this.calendar) {
        this.calendar.setOption("events", this.options.events);
        this.calendar.render();
      }
    },
  },
};
