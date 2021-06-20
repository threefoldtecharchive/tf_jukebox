<template>
  <external :url="url"></external>
</template>

<script>
module.exports = {
  props: { topic: String, queryparams: { type: Object, default: null } },
  computed: {
    url() {
      if (this.queryparams !== null) {
        let chatflowUrl = `/jukebox/chats/${this.topic}#/?noheader=yes&`;
        Object.keys(this.queryparams).forEach((key) => {
          chatflowUrl += `${key}=${this.queryparams[key]}&`;
        });
        return chatflowUrl;
      } else {
        return `/jukebox/chats/${this.topic}#/?noheader=yes`;
      }
    },
  },
  mounted() {
    if (window.marketplace_chatflow_end_listener_set === undefined) {
      // avoid setting multiple listeners
      window.marketplace_chatflow_end_listener_set = true;
      window.addEventListener("message", (event) => {
        let message = "chat ended: ";
        let len = message.length;
        if (
          event.origin != location.origin ||
          event.data.slice(0, len) != message
        )
          return;
        if (this.topic == "extend") {
          this.$router.push({
            name: "Solution",
            params: { type: this.queryparams["solution_type"] },
          });
        } else {
          let topic = event.data.slice(len);
          this.$router.push({
            name: "Solution",
            params: { type: topic },
          });
        }
      });
    }
  },
};
</script>
