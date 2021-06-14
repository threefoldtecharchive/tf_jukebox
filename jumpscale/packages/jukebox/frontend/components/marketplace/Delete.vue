<template>
  <base-dialog
    title="Cancel workload"
    v-model="dialog"
    :error="error"
    :loading="loading"
  >
    <template #default>
      Are you sure you want to cancel {{ deploymentname }}?
    </template>
    <template #actions>
      <v-btn text @click="close">Close</v-btn>
      <v-btn text color="error" @click="submit">Confirm</v-btn>
    </template>
  </base-dialog>
</template>

<script>
module.exports = {
  mixins: [dialog],
  props: ["deploymentname","solutiontype"],
  methods: {
    submit() {
      this.loading = true;
      this.error = null;
      this.$api.solutions
        .cancelDeployment(
          this.deploymentname,this.solutiontype
        )
        .then((response) => {
          console.log("cancelled");
          // this.$router.go(0);
          this.done("Deployment deleted");
        })
        .catch((err) => {
          console.log("failed");
          this.close();
        });
    },
  },
};
</script>
