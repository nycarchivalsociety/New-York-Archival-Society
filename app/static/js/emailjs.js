window.onload = function () {
  // Initialize EmailJS service
  emailjs.init("jYV8y8AwgFM2SI98x");

  // Add event listener for form submission
  document.getElementById("email-form").addEventListener("submit", sendMail);

  function sendMail(e) {
    e.preventDefault();

    // Fetch form data
    const params = getFormData();

    // Define EmailJS service and template IDs
    const serviceID = "service_ogwzo2j";
    const templateID = "template_lqrxlkm";

    // Send email using EmailJS
    emailjs.send(serviceID, templateID, params).then(
      (res) => {
        clearFormData();
        console.log(res);
        Swal.fire("Success!", "Your message sent successfully!", "success");
      },
      (error) => {
        Swal.fire({
          icon: "error",
          title: "Oops...",
          text: "Something went wrong!",
        });
      }
    );
  }

  // Function to get form data
  function getFormData() {
    return {
      from_name: document.getElementById("name").value,
      to_name: "The name of the recipient",
      subject: document.getElementById("subject").value,
      email: document.getElementById("email").value,
      message: document.getElementById("message").value,
    };
  }

  // Function to clear form data after successful submission
  function clearFormData() {
    document.getElementById("name").value = "";
    document.getElementById("email").value = "";
    document.getElementById("subject").value = "";
    document.getElementById("message").value = "";
  }
};
