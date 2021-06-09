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
            >
              <template slot="no-data">No {{solution.name.toLowerCase()}} instances available</p></template>

              <template v-slot:expanded-item="{ headers, item }">
                <td :colspan="headers.length" class="py-6 font-weight-black">
                    <p class="mb-4">Workloads</p>
                    <v-data-table
                      :loading="loading"
                      :headers="workloadHeaders"
                      :items="item.workloads"
                      class="elevation-1"
                      hide-default-footer

                    >
                      <template slot="no-data">No workloads available</p></template>
                    </v-data-table>
                </td>
              </template>

              <template v-slot:item.actions="{ item }">
                <v-tooltip top>
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn icon @click.stop="cancelDeployment(item)">
                      <v-icon v-bind="attrs" v-on="on" color="#810000"
                        >mdi-delete</v-icon
                      >
                    </v-btn>
                  </template>
                  <span>Delete</span>
                </v-tooltip>
              </template>


            </v-data-table>
          </v-card-text>
        </v-card>
      </template>
    </base-component>
    <cancel-deployment v-if="selected" v-model="dialogs.cancelDeployment" @done="getDeployedSolutions(solution.name)" :deploymentname="selected.name" :solutiontype="solution.name" ></cancel-deployment>
  </div>
</template>

<script>
module.exports = {
  props: {
    type: String,
  },

  components: {
    "cancel-deployment": httpVueLoader("./Delete.vue"),
  },
  data() {
    return {
      loading: true,
      selected: null,
      dialogs: {
        info: false,
        cancelDeployment: false,
      },
      mainheaders: [
        { text: "Deployment name", value: "name" },
        { text: "Farm name", value: "farm" },
        { text: "Active nodes", value: "total" },
        { text: "Actions", value: "actions", sortable: false },
        { text: '', value: 'data-table-expand' }
      ],
      workloadHeaders:[
        { text: "Id", value: "id" },
        { text: "IP address", value: "ip" },
        { text: "Cpu", value: "cpu" },
        { text: "Memory /MB", value: "memory" },
        { text: "Disk Size /MB", value: "disk" },
        { text: "Creation Time", value: "creation" },

      ],

      deployedSolutions: [],
      sections: SECTIONS,
    };
  },
  computed: {
    solution() {
      if(this.type==='all'){
        return {name: "Deployed Solutions",type: "all"}
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

    cancelDeployment(data) {
      this.selected = data;
      this.dialogs.cancelDeployment = true;
    },
    getDeployedSolutions(solution_type) {
        this.$api.solutions
          .getSolutions(solution_type)
          .then((response) => {
            this.deployedSolutions = response.data.data;

            for (let i = 0; i < this.deployedSolutions.length; i++) {
              for (let j = 0; j < this.deployedSolutions[i].workloads.length; j++) {
                let workload = this.deployedSolutions[i].workloads[j];
                // this.deployedSolutions[i]["id"] = workload.id
                this.deployedSolutions[i]["total"] = this.deployedSolutions[i].workloads.length
                workload["cpu"] = workload.capacity.cpu
                workload["memory"] = workload.capacity.memory
                workload["disk"] = workload.capacity.disk_size
                workload["ip"] = workload.network_connection[0].ipaddress
                workload["creation"] = new Date(workload.info.epoch* 1000).toLocaleString("en-GB");

              }
            }

          })
          .finally(() => {
            this.loading = false;
          });

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

</style>
