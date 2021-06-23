<template>
  <base-dialog
    title="Extend Deployment"
    v-model="dialog"
    :error="error"
    :loading="loading"
  >
    <template #default>
      Are you sure you want to extend {{ deploymentname }}?
    </template>
    <template #actions>
      <v-btn text @click="close">Close</v-btn>
      <v-btn :disabled="error" text color="error" @click="submit">Confirm</v-btn>
    </template>
  </base-dialog>
</template>

<script>
module.exports = {
  mixins: [dialog],
  props: {
    deploymentname: String,
    solutiontype: String,
  },
  methods: {
    submit() {
      this.loading = true;
      this.error = null;

      this.$api.solutions
        .extendDeployment(this.deploymentname, this.solutiontype)
        .then((response) => {
          this.done("Deployment extended");
        })
        .catch((err) => {
            this.loading = false;
            this.error = err.response.data;
        });
    },
  },
};
</script>
