<template>
  <div>
    <!-- <v-tabs v-model="tab" background-color="transparent" color="basil" grow> -->
    <!-- <v-tab :key="title">{{ title }}</v-tab> -->
    <!-- <v-tab :key="'moredetails'">More Details</v-tab> -->

    <!-- <v-tab-item :key="title"> -->
    <v-simple-table>
      <template v-slot:default>
        <tbody>
          <tr v-for="(item, key) in jsonobj" :key="key">
            <th v-if="!ignored.includes(key) && item !== ''">{{ key }}</th>
            <td v-if="typelist.includes(key)" class="pt-2">
              <v-text-field
                v-if="Object.keys(secrets).includes(key)"
                hide-details
                readonly
                solo
                flat
                :append-icon="secrets[key] ? 'mdi-eye' : 'mdi-eye-off'"
                @click:append="secrets[key] = !secrets[key]"
              >
                <template v-slot:prepend-inner>
                  <v-chip
                    class="ma-1"
                    v-bind:class="{ hide: !secrets[key] }"
                    v-for="node in item"
                    :key="node"
                    >{{ node }}</v-chip
                  >
                </template>
              </v-text-field>
              <v-text-field v-else hide-details readonly solo flat>
                <template v-slot:prepend-inner>
                  <v-chip class="ma-1" v-for="node in item" :key="node">{{
                    node
                  }}</v-chip>
                </template>
              </v-text-field>
            </td>
            <td v-else-if="typedict.includes(key)" class="pt-2">
              <v-text-field
                v-if="Object.keys(secrets).includes(key)"
                hide-details
                readonly
                solo
                flat
                :append-icon="secrets[key] ? 'mdi-eye' : 'mdi-eye-off'"
                @click:append="secrets[key] = !secrets[key]"
              >
                <template v-slot:prepend-inner>
                  <v-chip
                    class="ma-1"
                    v-bind:class="{ hide: !secrets[key] }"
                    v-for="(subItem, subkey) in item"
                    :key="subkey"
                  >
                    {{ subkey }}: {{ subItem }}</v-chip
                  >
                </template>
              </v-text-field>
              <v-text-field v-else hide-details readonly solo flat>
                <template v-slot:prepend-inner>
                  <v-chip
                    class="ma - 1"
                    v-for="(subItem, subkey) in item"
                    :key="subkey"
                  >
                    {{ subkey }}: {{ subItem }}</v-chip
                  >
                </template>
              </v-text-field>
            </td>
            <td v-else-if="!ignored.includes(key) && item !== ''">
              <v-text-field
                v-if="Object.keys(secrets).includes(key)"
                :value="item"
                hide-details
                readonly
                solo
                flat
                :append-icon="secrets[key] ? 'mdi-eye' : 'mdi-eye-off'"
                :type="secrets[key] ? 'text' : 'password'"
                @click:append="secrets[key] = !secrets[key]"
              >
              </v-text-field>
              <v-text-field
                :value="item"
                v-else
                hide-details
                readonly
                solo
                flat
              >
              </v-text-field>
            </td>
          </tr>
        </tbody>
      </template>
    </v-simple-table>
    <!-- </v-tab-item> -->
    <!-- <v-tab-item :key="'moredetails'">
        <v-card flat>
          <json-tree :raw="JSON.stringify(jsonobj)" id="test"></json-tree>
        </v-card>
      </v-tab-item> -->
    <!-- </v-tabs>
    <v-btn
      v-if="tab === 1"
      color="#52BE80"
      class="copy-btn ma-2 white--text"
      fab
      @click="copyjson()"
    >
      <v-icon dark> mdi-content-copy </v-icon>
    </v-btn> -->
  </div>
</template>

<script>
module.exports = {
  data() {
    return {
      tab: 0,
      lastObj: null,
    };
  },
  props: {
    title: String,
    jsonobj: {
      type: Object,
      default: () => ({}),
    },
    ignored: { type: Array, default: () => [] },
    typelist: { type: Array, default: () => [] },
    typedict: { type: Array, default: () => [] },
    secrets: { type: Object, default: {} },
  },
  methods: {
    copyjson() {
      const elem = document.createElement("textarea");
      elem.value = JSON.stringify(this.jsonobj);
      document.body.appendChild(elem);
      elem.select();
      document.execCommand("copy");
      document.body.removeChild(elem);
      this.alert("copied", "success");
    },
  },
  updated() {
    if (this.jsonobj !== this.lastObj) this.tab = 0;
    this.lastObj = this.jsonobj;
  },
  mounted() {
    this.lastObj = this.jsonobj;
  },
};
</script>


<style>
.copy-btn {
  position: absolute;
  right: 10;
  top: 10;
}
.hide {
  -webkit-text-security: disc; /* Default */
}
</style>
