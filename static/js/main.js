

function login() {
    let username = $("#username").val();
    let password = $("#password").val();
  
  
    $.ajax({
      type: "POST",
      url: "/login",
      data: {
        username_give: username,
        password_give: password,
      },
      success: function (response) {
        if (response.result === "success") {
          if (response.role === "user") {
            Swal.fire({
                title: 'Login Successful!',
                text: 'You will be redirected to the admin dashboard.',
                icon: 'success',
                confirmButtonText: 'Okay'
            }).then((result) => {
                if (result.isConfirmed) {
                    // Set cookie and redirect after user confirms
                    $.cookie("tokenuser", response["token"], { path: "/admin" });
                    window.location.replace("/admin");
                }
            });
        }
        
        } 
      
        else {
          alert(response["msg"]);
        }
      },
    });
  }
