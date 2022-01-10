var home = new Vue({
  el: '#home',
  data: {
    account: undefined,
    publickey: undefined,
    passphrase: undefined,
    error: undefined,
  },
  methods: {
    async logIn() {
      var data = {
        passphrase: this.passphrase,
        publickey: this.publickey
      }
      const res = await fetch('/login', {
        method: "POST", 
        body: JSON.stringify(data),
        headers: {
          'Content-Type': 'application/json'
        },
      }).then(response => {
        if (response.redirected) {
            window.location.href = response.url;
        }
        this.error = "Error invoking API. Status code: " + response.status + " Error: " + response.statusText;
      });
    },
    async createAccount() {
      const res = await fetch('/generateAccount');
      const data = await res.json();
      this.account = data;
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
        this.error = "Error invoking API. Status code: " + response.status + " Error: " + response.statusText;
      });;
    }
  },
  beforeMount() {
  },
  delimiters: ['[[',']]']
});