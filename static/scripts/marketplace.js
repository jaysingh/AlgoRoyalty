var marketplace = new Vue({
  el: '#marketplace',
  data: {
    account: undefined,
    assets: [],
    assetToBuy: undefined,
    passphrase: undefined,
    loading: false,
    error: undefined,
  },
  methods: {
    async getAccount() {
      const res = await fetch('/getaccountinfo');
      const data = await res.json();
      this.account = data;
    },
    async getAssets() {
      const res = await fetch('/getassets');
      const data = await res.json();
      this.assets = data.assets;
    },
    async buyNFTModal(asset) {
      this.assetToBuy = asset;
    },
    async buyNFT() {
      this.loading = true;
      data = {
        'app_id': Number(this.assetToBuy['app_id']),
        'asset_id': Number(this.assetToBuy['asset_id']),
        'passphrase': this.passphrase,
      };
      const res = await fetch('/buyNFT', {
        method: "POST", 
        body: JSON.stringify(data),
        headers: {
          'Content-Type': 'application/json'
        },
      }).then(response => {
        this.loading = false;
        if (response.redirected) {
            window.location.href = response.url;
        }
        this.error = "Error invoking API. Status code: " + response.status + " Error: " + response.statusText;
      });
    },
    async logOut() {
      const res = await fetch('/logout', {
        method: "POST", 
        body: JSON.stringify({}),
        headers: {
          'Content-Type': 'application/json'
        },
      }).then(response => {
        if (response.redirected) {
            window.location.href = response.url;
        }
      });
    }
  },
  async beforeMount(){
    await this.getAccount();
    await this.getAssets();
  },
  delimiters: ['[[',']]']
});