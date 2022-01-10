var mytransaction = new Vue({
  el: '#mytransaction',
  data: {
    account: undefined,
    transactions: [],
  },
  methods: {
    async getAccount() {
      const res = await fetch('/getaccountinfo');
      const data = await res.json();
      this.account = data;
    },
    async getTransactions() {
      const res = await fetch('/gettransactions');
      const data = await res.json();
      this.transactions = data.transactions.transactions;
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
      });;
    }
  },
  async beforeMount(){
    await this.getAccount()
    await this.getTransactions()
  },
  delimiters: ['[[',']]']
});