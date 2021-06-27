<template>
  <div>
    <base-dialog title="Deployment Details" v-model="dialog" :loading="loading">
      <template #default>
        <json-renderer
          v-if="!loading"
          title="Deployment"
          :jsonobj="deployment"
          :ignored="KeysIgnored"
          :typelist="KeysWithTypeList"
          :typedict="KeysWithTypeDict"
          :secrets="secrets"
        ></json-renderer>
      </template>
      <template #actions>
        <v-btn text @click="close">Close</v-btn>
      </template>
    </base-dialog>
  </div>
</template>

<script>
module.exports = {
  props: { deployment: Object },
  mixins: [dialog],
  data() {
    return {
      lastDeploymentName: "",
      KeysWithTypeList: ["pool_ids"],
      KeysWithTypeDict: ["secret_env"],
      KeysIgnored: [
        "nodes",
        "identity_name",
        "disk_type",
        "expiration_date",
        "poolExpire",
        "pool",
        "name",
        "farm",
        "total",
      ],
      secrets: { secret_env: false },
    };
  },
  methods: {
    getDeploymentSecret() {
      this.loading = true;
      this.error = null;

      this.$api.solutions
        .getDeploymentSecret(
          this.deployment.name,
          this.deployment.solution_type
        )
        .then((response) => {
          this.deployment["secret_env"] = response.data.data;
          this.lastDeploymentName = this.deployment.deployment_name;
        })
        .catch((err) => {
          this.error = err.response.data;
        })
        .finally(() => {
          this.loading = false;
        });
    },
  },
  updated() {
    if (
      this.deployment.deployment_name !== this.lastDeploymentName &&
      !this.loading
    ) {
      this.getDeploymentSecret();
    }
  },
};
</script>
