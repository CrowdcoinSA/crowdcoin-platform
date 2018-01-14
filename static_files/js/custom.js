//Contact Form

$(document).ready(function(){
 
$('#sendmsg').click(function(){
	$('#contactmsg').hide();
    $('#contact-message').text('Please wait...');
    $( "#contact-message" ).show(1000);
$.get("support_ticket_create", $("#contactmsg").serialize(),  function(response) {
    $('#contactmsg').find("input[type=text], textarea").val("");
    $('#contact-message').html(response);
    $('#contactmsg').show(1000);
});
 
});	
});	