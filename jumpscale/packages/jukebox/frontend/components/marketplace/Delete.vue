<template>
  <base-dialog
    title="Cancel workload"
    v-model="dialog"
    :error="error"
    :loading="loading"
  >
    <template #default v-if="wid != null">
      Are you sure you want to cancel {{wid}} from your deployment {{ deploymentname }}?
    </template>
    <template #default v-else>
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
  props: {
    deploymentname:String,
    wid:{type:Number,default:null},
    solutiontype:String
  },
  methods: {
    submit() {
      debugger;
      this.loading = true;
      this.error = null;
      if(this.wid == null){
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
      }
      else{
        this.$api.solutions
          .cancelNode(
            this.deploymentname,this.wid,this.solutiontype
          )
          .then((response) => {
            console.log("cancelled");
            // this.$router.go(0);
            this.done("Node deleted");
          })
          .catch((err) => {
            console.log("failed");
            this.close();
          });

      }
    },
  },
};
</script>
