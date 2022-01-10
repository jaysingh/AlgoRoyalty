var createasset = new Vue({
  el: '#createasset',
  data: {
    account: undefined,
    publickey: undefined,
    nft_url: undefined,
    nft_hash: undefined,
    nft_name: undefined,
    nft_unit_name: undefined,
    nft_description: undefined,
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
    async createAsset() {
      this.loading = true;
      var data = {
        nftMetadata: {
          name: this.nft_name,
          unit_name: this.nft_unit_name,
          description: this.ft_description,
          url: this.nft_url,
          nft_integrity: this.nft_hash,
          properties: {},
        },
        passphrase: this.passphrase
      }
      const res = await fetch('/createNFT', {
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
    async onChange(event) {
        let file = document.getElementById("formFileLg").files[0];
        let formData = new FormData();
     
        formData.append("file", file);
        const res = await fetch('/uploadToIPFS', {method: "POST", body: formData});
        const data = await res.json();
        this.nft_url = data.url;
        this.nft_hash = data.hash;
    },
    logOut: function () {
      this.account = undefined;
      this.$cookies.remove('publickey');
    }
  },
  async beforeMount(){
    await this.getAccount()
  },
  delimiters: ['[[',']]']
});