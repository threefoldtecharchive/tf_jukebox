<template>
  <div>
    <v-parallax :src="jukebox_data.bg" height="100%">
      <v-row align="center" justify="center">
        <v-col class="text-center" cols="12">
          <h1 style="font-size: 60" class="mb-2">{{ jukebox_data.header }}</h1>
          <h3 class="subheading">{{ jukebox_data.subheader }}</h3>
          <v-btn
            color="#4472B5"
            class="mt-8 mx-2"
            dark
            large
            @click.stop="viewWorkloads()"
            >Jukebox deployer</v-btn
          >

        </v-col>
      </v-row>
    </v-parallax>
  </div>
</template>

<script>
module.exports = {
  data() {
    return {
      jukebox_data: APPS["jukebox"],
    };
  },
  methods: {
    openChatflow(topic) {
      this.$router.push({
        name: "Chatflow",
        params: { topic: topic },
      });
    },
    viewWorkloads() {
      this.$router.push({ name: "Marketplace" });
    },
  },
};
</script>
