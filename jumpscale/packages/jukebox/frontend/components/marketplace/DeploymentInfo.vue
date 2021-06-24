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
          debugger;
          this.deployment["secret_env"] = response.data.data;
        })
        .catch((err) => {
          this.error = err.response.data;
        })
        .finally(() => {
          this.loading = false;
        });
    },
  },
  mounted() {
    this.getDeploymentSecret();
  },
};
</script>
