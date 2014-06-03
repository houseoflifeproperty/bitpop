var bg_window;

$(document).ready(function(){
  bg_window = chrome.extension.getBackgroundPage();

  loadOptions();

  $("#show_protocol").change(function(event) {
          $(".url").text($(this).is(":checked") ? "http://www.google.com/chrome" : "www.google.com/chrome");
  });

  $("#primary_color").change(function(event) {
          $(".title").css("color", $(this).val());
  });

  $("#secondary_color").change(function(event) {
          $(".subtitle").css("color", $(this).val());
  });

  $("#border_color").change(function(event) {
          $(".spacer").css("border-bottom", "1px solid "+ $(this).val());
  });

  $("#background_color").change(function(event) {
          $(".links").css("background-color", $(this).val());
          $(".links_inline").css("background-color", $(this).val());
          var hover_color = $("#hover_color").val();
          var bg_color = $("#background_color").val();
          $(".details").hover(function () {
                  $(this).css("background-color", hover_color);
          }, function () {
                  $(this).css("background-color", bg_color);
          });
  });

  $("#hover_color").change(function(event) {
          var hover_color = $(this).val();
          var bg_color = $("#background_color").val();
          $(".details").hover(function () {
                  $(this).css("background-color", hover_color);
          }, function () {
                  $(this).css("background-color", bg_color);
          });
  });

});


function applySyncing() {
}

function saveOptions() {

	//check custom width
	if($("#width").val().match(/^\d+$/) == null || $("#width").val() > 800) {
		alert("Please provide a valid width between 0 and 800 px");
		$("#width_value").focus();
		return false;
	}

	//check link num
	if($("#link_num").val().match(/^\d+$/) == null) {
		alert("Please provide a valid number");
		$("#link_num").focus();
		return false;
	}


	//save list style
	localStorage["list_style"] = $("input[name=list_style]:checked").val();

	//save show_protocol
	localStorage["show_protocol"] = $("#show_protocol").is(":checked") ? "yes" : "no";

	//save typed_only
	localStorage["typed_only"] = $("#typed_only").is(":checked") ? "yes" : "no";

	//save link_num
	localStorage["link_num"] = $("#link_num").val();

	//save colors
	localStorage["primary_color"] = $("#primary_color").val();
	localStorage["secondary_color"] = $("#secondary_color").val();
	localStorage["hover_color"] = $("#hover_color").val();
	localStorage["border_color"] = $("#border_color").val();
	localStorage["background_color"] = $("#background_color").val();

	//save middle
	localStorage["middle"] = $("input[name=middle]:checked").val();

	//save width
	localStorage["width"] = $("#width").val();

	//reset ignore list
	if($("#reset_ignore").is(":checked")) {
		localStorage["ignore"] = JSON.stringify(new Array());
		//$("#reset_ignore").attr("checked", false);
		//$("#reset_ignore_label").text("Reset Ignore List (" + JSON.parse(localStorage["ignore"]).length + " items)");
	} else if($("#ignore_list").val().length > 0) {
		var ignoreList = JSON.parse(localStorage["ignore"]);
		var ignoreListNew = new Array();
		for(var i=0;i<ignoreList.length;i++) {
			if(ignoreList[i] != $("#ignore_list").val()) {
				ignoreListNew.push(ignoreList[i]);
			}
		}
		localStorage["ignore"] = JSON.stringify(ignoreListNew);
	}

        applySyncing();

	$("#form_status").show();
	setTimeout(function() {
		$("#form_status").fadeOut("slow");
	}, 1000);

	//refresh history
	//chrome.extension.getBackgroundPage().readHistory();

	loadOptions();

}

function loadOptions() {

	//default options
	if(!localStorage["list_style"]) {
		localStorage["list_style"] = "double_title_url";
	}

	if(!localStorage["show_protocol"]) {
		localStorage["show_protocol"] = "no";
	}

	if(!localStorage["typed_only"]) {
		localStorage["typed_only"] = "no";
	}

	if(!localStorage["link_num"]) {
		localStorage["link_num"] = "12";
	}

	if(!localStorage["primary_color"]) {
		localStorage["primary_color"] = "#858586";
	}

	if(!localStorage["secondary_color"]) {
		localStorage["secondary_color"] = "#A5B7A5";
	}

	if(!localStorage["hover_color"]) {
		localStorage["hover_color"] = "#CDE5FF";
	}

	if(!localStorage["border_color"]) {
		localStorage["border_color"] = "#F1F8FF";
	}

	if(!localStorage["background_color"]) {
		localStorage["background_color"] = "#FFFFFF";
	}

	if(!localStorage["middle"]) {
		localStorage["middle"] = "foreground";
	}

	if(!localStorage["width"]) {
		localStorage["width"] = "600";
	}

	if(!localStorage["ignore"]) {
		localStorage["ignore"] = JSON.stringify(new Array());
	}

	//load
	$("#list_style_"+localStorage["list_style"]).attr("checked", true);

	$("#show_protocol").attr("checked", localStorage["show_protocol"] == "yes");
	$("#typed_only").attr("checked", localStorage["typed_only"] == "yes");

	$("#link_num").val(localStorage["link_num"]);

	$("#primary_color").val(localStorage["primary_color"]);
	$("#secondary_color").val(localStorage["secondary_color"]);
	$("#hover_color").val(localStorage["hover_color"]);
	$("#border_color").val(localStorage["border_color"]);
	$("#background_color").val(localStorage["background_color"]);

	$("#middle_"+localStorage["middle"]).attr("checked", true);

	$("#width").val(localStorage["width"]);

	//protocol
	$(".url").text(localStorage["show_protocol"] == "yes" ? "http://www.google.com/chrome" : "www.google.com/chrome");

	//ignore list
	var ignoreList = JSON.parse(localStorage["ignore"]).reverse();
	$("#ignore_list").find("option").remove();
	$("#ignore_list").
			append($("<option></option>").
			attr("value","").
			text("Select ignored URL to remove from the list:"));

	for(var i=0;i<ignoreList.length;i++) {
		$("#ignore_list").
			append($("<option></option>").
			attr("value",ignoreList[i]).
			text(ignoreList[i]));
	}

	$("#reset_ignore_label").text("Reset All (" + ignoreList.length + " items)");

  	//colors
	resetColors();
}

function resetOptions() {
	$("#options_form")[0].reset();

	resetColors();

	$("#primary_color")[0].color.fromString($("#primary_color").val());
	$("#secondary_color")[0].color.fromString($("#secondary_color").val());
	$("#hover_color")[0].color.fromString($("#hover_color").val());
	$("#border_color")[0].color.fromString($("#border_color").val());
	$("#background_color")[0].color.fromString($("#background_color").val());
}

function resetColors() {
	$(".title").css("color", $("#primary_color").val());

	$(".subtitle").css("color", $("#secondary_color").val());

	$(".spacer").css("border-bottom", "1px solid "+ $("#border_color").val());

	$(".links").css("background-color", $("#background_color").val());
	$(".links_inline").css("background-color", $("#background_color").val());
	var hover_color = $("#hover_color").val();
	var bg_color = $("#background_color").val();
	$(".details").hover(function () {
		$(this).css("background-color", hover_color);
	}, function () {
		$(this).css("background-color", bg_color);
	});
}
