<template>
  <base-dialog
    title="Wallet Topup"
    v-model="dialog"
    :error="error"
    :loading="loading"

  >
    <template #default>
        <strong v-if="!loading && wallet.amount > 0"> Please fund your wallet for the extension of the pools to extend your nodes expiration with an amount of {{wallet.amount}} {{wallet.balance.asset}}</strong>

        <v-simple-table >
        <template v-slot:default>
            <tbody>
            <tr>
                <td>Network</td>
                <td>{{ wallet.network }}</td>
            </tr>
            <tr>
                <td>Address</td>
                <td>{{ wallet.address }}</td>
            </tr>
            <tr>
                <td>Balance</td>
                <td class="pt-1" >
                    <v-chip
                    outlined
                    class="ma-2"
                    >
                    {{ wallet.balance.amount }} {{ wallet.balance.asset }}
                    </v-chip>
                </td>
            </tr>
            <tr  v-if="wallet.qrcode">
                <td>QRCode</td>
                <td class="pt-1">
                <div class="text-left ma-1">
                    <v-tooltip top>
                    <template v-slot:activator="{ on, attrs }" >
                        <img
                        v-bind="attrs"
                        v-on="on"
                        style="border: 1px dashed #85929e"
                        :src="`data:image/png;base64,${wallet.qrcode}`"
                        />
                    </template>
                    <span
                        >Scan the QRCode to topup wallet using Threefold Connect
                        application</span
                    >
                    </v-tooltip>
                </div>
                </td>
            </tr>
            </tbody>
        </template>
        </v-simple-table>
    </template>

    <template #actions>
        <v-btn text @click="close">Close</v-btn>
    </template>
  </base-dialog>
</template>

<script>
module.exports = {
  mixins: [dialog],
  data() {
    return {
      wallet: {balance:{}},
      loading:false
    };
  },
  methods: {
      getWalletInfo(){
        this.loading = true
        this.$api.wallet
        .getTopupInfo()
        .then((response) => {
            this.wallet = response.data.data;
        })
        .finally(() => {
          this.loading = false;
        });
      }
  },
  mounted() {
    this.getWalletInfo();
  },

};
</script>
