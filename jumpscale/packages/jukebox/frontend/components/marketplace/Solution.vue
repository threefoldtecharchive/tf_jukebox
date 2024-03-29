<template>
  <div>
    <base-component title="Apps Menu" icon="mdi-menu-left" url="/marketplace" :loading="loading">
      <template #default>
        <v-card class="pa-3 ml-3">
          <v-card-title class="headline">
            <v-avatar v-if="solution.image" size="50px" class="mr-5" tile>
              <v-img :src="solution.image"></v-img>
            </v-avatar>
            <span>{{solution.name}}</span>
            <v-tooltip top>
              <template v-if="solution.helpLink" v-slot:activator="{ on, attrs }">
                <a
                  v-if="type!='all'"
                  class="chatflowInfo"
                  :href="solution.helpLink"
                  target="blank"
                >
                  <v-icon
                    color="primary"
                    large
                    v-bind="attrs"
                    v-on="on"
                    right
                  >mdi-information-outline</v-icon>
                </a>
              </template>
              <span>Go to Wiki</span>
            </v-tooltip>
          </v-card-title>
          <v-card-text v-if="type!='all'">
            <span>{{solution.description}}</span>
            <br />
            <br />
            <v-btn color="primary" @click.stop="restart(solution.type)">New</v-btn>
            <v-btn
              color="primary"
              v-if="started(solution.type)"
              @click.stop="open(solution.type)"
            >Continue</v-btn>
          </v-card-text>

          <v-card-text>
            <v-divider class="my-5"></v-divider>

            <v-data-table
              :loading="loading"
              :headers="mainheaders"
              :items="deployedSolutions"
              class="elevation-1"
              show-expand
              item-key="name"

            >
              <template slot="no-data">No {{solution.name.toLowerCase()}} instances available</p></template>

              <template v-slot:expanded-item="{ headers, item }">

                <td :colspan="headers.length" class="py-6 font-weight-black">
                    <p class="mb-4">Workloads</p>
                    <v-data-table
                      :loading="loading"
                      :headers="workloadHeaders"
                      :items="item.nodes"
                      :item-class="itemRowBackground"
                      class="elevation-1"
                      hide-default-footer
                      sort-by="state"
                      sort-desc

                    >
                      <template slot="no-data">No workloads available</p></template>
                      <template v-slot:item.ipv6="{ item }">
                        <a :href="`http://[${item.ipv6}]`" target="_blank" v-if="item.state != 'DELETED'">{{item.ipv6}}</a>
                      </template>
                      <template v-slot:item.ipv4="{ item }">
                        <span v-if="item.state != 'DELETED'">{{item.ipv4}}</span>
                      </template>
                      <template v-slot:item.actions="{ item }">
                        <v-tooltip top v-if="item.state != 'DELETED'">
                          <template v-slot:activator="{ on, attrs }">
                            <v-btn icon @click.stop="cancelNode(item.deploymentName,item.wid)">
                              <v-icon v-bind="attrs" v-on="on" color="#810000"
                                >mdi-delete</v-icon
                              >
                            </v-btn>
                          </template>
                          <span>Delete</span>
                        </v-tooltip>
                      </template>
                    </v-data-table>
                </td>
              </template>

              <template v-slot:item.actions="{ item }">
                <v-tooltip top>
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn icon @click.stop="openExtendChatflow(item.name)">
                      <v-icon v-bind="attrs" v-on="on" color="#1b4f72"
                        >mdi-plus-network-outline</v-icon
                      >
                    </v-btn>
                  </template>
                  <span>Add Nodes</span>
                </v-tooltip>
                <v-tooltip top>
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn icon @click.stop="showInfo(item)">
                      <v-icon v-bind="attrs" v-on="on" color="#206A5D"
                        >mdi-information-outline</v-icon
                      >
                    </v-btn>
                  </template>
                  <span>Show Information</span>
                </v-tooltip>
                <v-tooltip top>
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn icon @click.stop="cancelDeployment(item.name)">
                      <v-icon v-bind="attrs" v-on="on" color="#810000"
                        >mdi-delete</v-icon
                      >
                    </v-btn>
                  </template>
                  <span>Delete</span>
                </v-tooltip>
                <v-tooltip top>
                  <template v-slot:activator="{ on, attrs }">
                    <div v-bind="attrs" v-on="on" class="switch-div" >
                    <v-switch
                      v-model="item.autoextend"
                      @click.stop="switchAutoExtend(item)"
                      dense
                    ></v-switch>
                    </div>
                  </template>
                  <span>Auto Extend Deployment</span>
                </v-tooltip>
                <v-tooltip top v-if="item.poolExpire && item.autoextend">
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn icon @click.stop="extendDeployment(item.name)">
                      <v-icon v-bind="attrs" v-on="on" color="#1b4f72"
                        >mdi-arrow-top-right-thick</v-icon
                      >
                    </v-btn>
                  </template>
                  <span>Deployment about to expire. Click to extend</span>
                </v-tooltip>
                <v-tooltip top v-if="item.activeworkloads !== item.total">
                  <template v-slot:activator="{ on, attrs }">
                    <v-icon v-bind="attrs" v-on="on" color="#810000"
                      >mdi-alert-outline</v-icon
                    >
                  </template>
                  <span>{{ item.total - item.activeworkloads }} node(s) of this deployment went down</span>
                </v-tooltip>
              </template>


            </v-data-table>
          </v-card-text>
        </v-card>
      </template>
    </base-component>
    <cancel-deployment v-if="selected" v-model="dialogs.cancelDeployment" @done="getDeployedSolutions(type)" :deploymentname="selected" :wid="selectedWid" :solutiontype="type" ></cancel-deployment>
    <extend-deployment v-if="selected" v-model="dialogs.extendDeployment" @done="getDeployedSolutions(type)" :deploymentname="selected" :solutiontype="type" ></extend-deployment>
    <info-deployment v-if="selectedDeployment" v-model="dialogs.infoDeployment" :deployment="selectedDeployment"></info-deployment>
  </div>
</template>

<script>
module.exports = {
  props: {
    type: String,
  },

  components: {
    "cancel-deployment": httpVueLoader("./Delete.vue"),
    "extend-deployment": httpVueLoader("./Extend.vue"),
    "info-deployment": httpVueLoader("./DeploymentInfo.vue"),
  },
  data() {
    return {
      loading: true,
      selected: null,
      selectedWid: null,
      selectedDeployment: null,
      dialogs: {
        info: false,
        cancelDeployment: false,
        extendDeployment: false,
        infoDeployment: false,
      },
      mainheaders: [
        { text: "Deployment Name", value: "name" },
        { text: "Farm Name", value: "farm" },
        { text: "Pool ID", value: "pool" },
        { text: "Total Active Nodes", value: "total" },
        { text: "Expiration Date", value: "expiration" },
        { text: "Actions", value: "actions", sortable: false },
        { text: "", value: "data-table-expand" },
      ],
      workloadHeaders: [
        { text: "ID", value: "wid" },
        { text: "IPv4 address", value: "ipv4" },
        { text: "IPv6 address", value: "ipv6" },
        { text: "Cpu", value: "cpu" },
        { text: "Memory /GB", value: "memory" },
        { text: "Disk Size /GB", value: "disk" },
        { text: "State", value: "state" },
        { text: "Creation Time", value: "creation" },
        { text: "Actions", value: "actions", sortable: false },
      ],

      deployedSolutions: [],
      sections: SECTIONS,
    };
  },
  computed: {
    solution() {
      if (this.type === "all") {
        return { name: "Deployed Solutions", type: "all" };
      }
      for (section in this.sections) {
        if (Object.keys(this.sections[section].apps).includes(this.type)) {
          return this.sections[section].apps[this.type];
        }
      }
    },
  },
  methods: {
    open(solutionId) {
      this.$router.push({
        name: "SolutionChatflow",
        params: { topic: solutionId },
      });
    },
    restart(solutionId) {
      localStorage.removeItem(solutionId);
      this.open(solutionId);
    },
    started(solution_type) {
      return localStorage.hasOwnProperty(solution_type);
    },

    cancelDeployment(deploymentName) {
      this.selected = deploymentName;
      this.selectedWid = null;
      this.dialogs.cancelDeployment = true;
    },
    cancelNode(deploymentName, wid) {
      this.selected = deploymentName;
      this.selectedWid = wid;
      this.dialogs.cancelDeployment = true;
    },
    getDeployedSolutions(solution_type) {
      this.$api.solutions
        .getSolutions(solution_type)
        .then((response) => {
          this.deployedSolutions = response.data.data;

          for (let i = 0; i < this.deployedSolutions.length; i++) {
            this.deployedSolutions[i].pool =
              this.deployedSolutions[i].pool_ids[0];
            this.deployedSolutions[i]["poolExpire"] =
              this.deployedSolutions[i].expiration_date <
              Date.now() / 1000 + 60 * 60 * 24 * 2;
            this.deployedSolutions[i].expiration = new Date(
              this.deployedSolutions[i].expiration_date * 1000
            ).toLocaleString("en-GB");
            this.deployedSolutions[i].autoextend =
              this.deployedSolutions[i].auto_extend;
            this.deployedSolutions[i].name =
              this.deployedSolutions[i].deployment_name;
            this.deployedSolutions[i].farm =
              this.deployedSolutions[i].farm_name;

            this.deployedSolutions[i]["total"] =
              this.deployedSolutions[i].nodes_count;

            let activeWorkloads = 0;
            for (let j = 0; j < this.deployedSolutions[i].nodes.length; j++) {
              let workload = this.deployedSolutions[i].nodes[j];
              workload["cpu"] = this.deployedSolutions[i].cpu;
              workload["memory"] = this.deployedSolutions[i].memory / 1024;
              workload["disk"] = this.deployedSolutions[i].disk_size / 1024;
              workload["ipv4"] = workload.ipv4_address;
              workload["ipv6"] = workload.ipv6_address;
              workload["deploymentName"] =
                this.deployedSolutions[i].deployment_name;
              workload["creation"] = new Date(
                workload.creation_time * 1000
              ).toLocaleString("en-GB");
              // count number of workloads that are active and deployed
              if (workload.state == "DEPLOYED") {
                activeWorkloads += 1;
              }
            }
            this.deployedSolutions[i]["activeworkloads"] = activeWorkloads;
          }
        })
        .finally(() => {
          this.loading = false;
        });
    },
    switchAutoExtend(item) {
      this.loading = false;
      this.$api.solutions
        .switchAutoExtend(item.name, this.type, item.autoextend)
        .then((response) => {
          this.getDeployedSolutions(this.type);
        })
        .finally(() => {
          this.loading = false;
        });
    },
    itemRowBackground(item) {
      return item.state == "DELETED" ? "deleted-node" : "";
    },
    openExtendChatflow(deploymentName) {
      let queryparams = {
        deployment_name: deploymentName,
        solution_type: this.type,
      };
      this.$router.push({
        name: "SolutionChatflow",
        params: { topic: "extend", queryparams: queryparams },
      });
    },
    extendDeployment(name) {
      this.selected = name;
      this.dialogs.extendDeployment = true;
    },
    showInfo(deployment) {
      this.selectedDeployment = deployment;
      this.dialogs.infoDeployment = true;
    },
  },
  mounted() {
    this.getDeployedSolutions(this.type);
  },
};
</script>

<style scoped>
a.chatflowInfo {
  text-decoration: none;
  position: absolute;
  right: 10px;
  top: 10px;
}

.v-data-table__expanded.v-data-table__expanded__content {
  box-shadow: none !important;
}
.switch-div {
  display: inline-block;
}
.deleted-node {
  color: rgb(150, 0, 0, 0.7);
}
</style>
