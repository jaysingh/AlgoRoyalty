var myassets = new Vue({
  el: '#myassets',
  data: {
    account: undefined,
    assets: [],
    assetToSell: undefined,
    price: undefined,
    royalty: {
      state: 0
    },
    royalty_groups: [],
    chain_groups: [],
    passphrase: undefined,
    loading: false,
    error:undefined,
  },
  methods: {
    async getAccount() {
      const res = await fetch('/getaccountinfo');
      const data = await res.json();
      this.account = data;
    },
    async getAssets() {
      const res = await fetch('/getmyassets');
      const data = await res.json();
      this.assets = data.assets;
    },
    async sellNFTModal(asset) {
      this.assetToSell = asset;
      if (asset['royalty']) {
        this.royalty.state = asset['royalty']['state'];
        this.royalty_groups = asset['royalty']['royalty_groups'];
        this.chain_groups = asset['royalty']['chain_groups'];
        this.price = asset['price'];
      }
    },
    onRoyaltyChange(event) {
      if (this.royalty.state === 0) {
        this.royalty_groups = [];
        return;
      }
      if (this.royalty.state === 1) {
        this.royalty_groups = [{
          address: this.assetToSell['creator_str'],
          royalty: 5,
        }];
        return;
      }
      if (this.royalty.state === 2) {
        if (this.assetToSell['royalty']) {
          this.royalty.state = this.assetToSell['royalty']['state'];
          this.royalty_groups = this.assetToSell['royalty']['royalty_groups'];
          return;
        }
        this.royalty_groups = [{
          address: this.assetToSell['creator_str'],
          royalty: 5,
        }];
        return;
      }
      if (this.royalty.state === 3) {
        if (this.assetToSell['royalty']) {
          this.royalty.state = this.assetToSell['royalty']['state'];
          this.chain_groups = this.assetToSell['royalty']['chain_groups'];
          return;
        }
        this.chain_groups = [{
          level: this.chain_groups.length,
          address: '',
          royalty: 0,
        }];
        return;
      }
    },
    async sellNFT() {
      this.loading = true;
      royalty_data = this.getRoyalty();
      data = {
        'app_id': Number(this.assetToSell['app_id']),
        'asset_id': Number(this.assetToSell['asset_id']),
        'price': Number(this.price),
        'passphrase': this.passphrase,
        'royalty': royalty_data
      };
      const res = await fetch('/placeNFTForSale', {
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
    getRoyalty: function () {
      if (this.royalty.state === 0) {
        return {
          'state': 0,
          'royalty_groups': []
        }
      }
      if (this.royalty.state === 1 || this.royalty.state === 2) {
        royalty_groups_local = [];
        for (const element of this.royalty_groups) {
            if (element && element.address && element.royalty && element.royalty > 0) {
              royalty_groups_local.push({
                address: element.address,
                royalty: Number(element.royalty),
              });
            }
        }
        return {
          'state': this.royalty.state,
          'royalty_groups': royalty_groups_local,
          'chain_groups': []
        }
      }
      if (this.royalty.state === 3) {
        chain_groups_local = [];
        for (const element of this.chain_groups) {
            if (element.royalty && element.royalty > 0) {
              chain_groups_local.push({
                level: element.level,
                address: element.address,
                royalty: Number(element.royalty),
              });
            }
        }
        return {
          'state': this.royalty.state,
          'royalty_groups': [],
          'chain_groups': chain_groups_local
        }
      }
    },
    addRoyalty: function () {
      this.royalty_groups.push({
        address: undefined,
        royalty: undefined,
      });
    },
    addLevel: function () {
      this.chain_groups.push({
        level: this.chain_groups.length,
        address: '',
        royalty: 0,
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