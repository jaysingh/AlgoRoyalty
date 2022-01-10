Vue.filter('formatDate', function(value) {
    if (value) {
        return moment.unix(String(value)).format('YYYY-MM-DDThh:mm:ss');
    }
});

Vue.filter('algos', function(value) {
    if (value) {
        return (value / 1000000.0).toFixed(6);
    }
})