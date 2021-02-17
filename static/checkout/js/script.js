/* Handle any errors returns from Checkout  */
var handleResult = function(result) {
    if (result.error) {
      var displayError = document.getElementById("error-message");
      displayError.textContent = result.error.message;
    }
  };

  // Create a Checkout Session with the selected quantity
  var createCheckoutSession = function() {
    var inputEl = document.getElementById("quantity-input");
    var quantity = parseInt(inputEl.value);
    return fetch("/checkout/create-checkout-session/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        quantity: quantity,
      })
    }).then(function(result) {
      return result.json();
    });
  };

  /* Get your Stripe publishable key to initialize Stripe.js */
  fetch("/checkout/config")
    .then(function(result) {
      return result.json();
    })
    .then(function(json) {
      window.config = json;
      var stripe = Stripe(config.publicKey);
      // Setup event handler to create a Checkout Session on submit
      document.querySelector("#submit").addEventListener("click", function(evt) {
        createCheckoutSession().then(function(data) {
          stripe
            .redirectToCheckout({
              sessionId: data.sessionId
            })
            .then(handleResult);
        });
      });
    });