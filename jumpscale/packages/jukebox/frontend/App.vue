<template>
  <v-app>
    <v-app-bar app>
      <router-link to="/" style="text-decoration: none">
        <v-row>
          <img
            class="ml-2"
            src="./assets/jukebox_logo.png"
            height="80"
            width="100"
          />
        </v-row>
      </router-link>
      <v-spacer></v-spacer>


      <div v-if="this.notification">
        <v-badge
          color="warning"
          overlap
          class="mr-4"
          icon="mdi-alert-circle-outline"
          left
        >
        <v-btn text @click="showWallet()">
          <v-icon left>mdi-bank</v-icon>
          Fund Wallet
        </v-btn>
        </v-badge>
      </div>
      <div v-else>
       <v-btn text @click="showWallet()">
          <v-icon left>mdi-bank</v-icon>
          Fund Wallet
        </v-btn>
      </div>

      <v-menu v-model="menu" :close-on-content-click="false" offset-x>
        <template v-slot:activator="{ on }">
          <v-btn text v-on="on">
            <v-icon left>mdi-account</v-icon>
            {{ user.username }}
          </v-btn>
        </template>
        <v-card>
          <v-list>
            <v-list-item>
              <v-list-item-avatar>
                <v-avatar color="primary">
                  <v-icon dark>mdi-account-circle</v-icon>
                </v-avatar>
              </v-list-item-avatar>
              <v-list-item-content>
                <v-list-item-title>{{ user.username }}</v-list-item-title>
                <v-list-item-subtitle>{{ user.email }}</v-list-item-subtitle>
              </v-list-item-content>
            </v-list-item>
            <v-list-item>
              <v-list-item-content>
                <v-btn text color="blue" :to="'/terms'"
                  >Terms and Conditions</v-btn
                >
              </v-list-item-content>
            </v-list-item>
            <v-list-item>
              <v-list-item-content>
                <v-btn text color="blue" :to="'/disclaimer'">Disclaimer</v-btn>
              </v-list-item-content>
            </v-list-item>
            <v-list-item>
              <v-list-item-content>
                <v-btn
                  text
                  :link="true"
                  color="blue"
                  href="https://manual.threefold.io/#/"
                  target="_blank"
                  >Manual</v-btn
                >
              </v-list-item-content>
            </v-list-item>
          </v-list>
          <v-divider></v-divider>
          <v-card-actions>
            <v-btn block text @click.stop="logout">
              <v-icon color="primary" class="mr-2" left>mdi-exit-to-app</v-icon
              >Logout
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-menu>

      <wallet-dialog
        v-if="dialogs.wallet"
        v-model="dialogs.wallet"
      ></wallet-dialog>
    </v-app-bar>
     <v-dialog v-if="dialogChanged" v-model="dialogChanged" width="400">
        <v-alert
      v-if="dialogChanged"
      border="bottom"
      colored-border
      type="warning"
      elevation="2"
      class="mb-0"
    > <strong> Warning <br /> </strong>
    <p><span v-html="warningMessage"></span></p>
    </v-alert>
      </v-dialog>

    <v-main>
      <router-view></router-view>
      <popup></popup>
    </v-main>
  </v-app>
</template>

<script>
module.exports = {
  data() {
    return {
      user: {},
      menu: false,
      mini: false,
      walletInfo: null,
      warningMessage: null,
      notification: false,
      dialogChanged: false,
      wallet: {},
      dialogs: {
        wallet: false,
      },
    };
  },
  components: {
    "wallet-dialog": httpVueLoader("./components/Wallet.vue"),
  },
  methods: {
    getCurrentUser() {
      this.$api.admins.getCurrentUser().then((response) => {
        this.user = response.data;
      });
    },
    logout() {
      // clear cache on logout
      var backlen = history.length;
      history.go(-backlen);
      window.location.href = "/auth/logout";
    },
    showWallet() {
      this.dialogs.wallet = true;
    },
    getWalletInfo() {
      this.$api.wallet
        .getTopupInfo()
        .then((response) => {
          let newWallet = response.data.data;
          if (newWallet === this.wallet || this.wallet.amount === newWallet.amount) {
            this.dialogChanged = false;
            return
          }
          this.wallet = newWallet;
          if (this.wallet.amount > 0) {
            this.dialogChanged = true;
            this.notification = true;
            this.warningMessage =
              "Some of your deployemts that have auto extend enabled are about to expire. <br/> To ensure the auto extension, you need to fund the wallet through clicking the fund wallet button found in the upper right.";
          }
          else {
            this.notification = false;
          }
        })
        .finally(() => {});
    },
  },
  mounted() {
    this.getCurrentUser();
  },
  updated () {
    this.getWalletInfo();

  }
};
</script>
