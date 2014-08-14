$(document).ready(function(){
        displayLinks();
        setStyling();
});

function displayLinks() {
        var items = chrome.extension.getBackgroundPage().cache.options.history;
        var displayProtocol = localStorage["show_protocol"] == "yes";
        var style = localStorage["list_style"];

        var $links = $("<div/>", {class: style.indexOf("inline_") == 0 ? "links_inline" : "links"});
        for(var i=0;i<items.length;i++) {

                var title = items[i].title ? items[i].title : items[i].url;
                var url = displayProtocol ? items[i].url : items[i].url.replace(/^\w+\:\/\//, "");

                //remove trailing slash
                if(url.charAt(url.length-1) == "/") {
                        url = url.substr(0, url.length-1);
                }

                var $details = $("<div/>", {class:"details"});


                var $icon = $("<img/>", {class:"icon", src:"chrome://favicon/"+items[i].url});

                var $remove = $("<a/>", {class:"remove", href:"#", title:"Remove", text:"x"})
                                                .data("url", items[i].url)
                                                .click(function(event) {
                                                        removeUrl($(this));
                                                        event.preventDefault();
                                                });

                $details.append($icon);
                $details.append($remove);

                var $info = $("<div/>", {class:"info"})
                                                .data("url", items[i].url)
                                                .mousedown(function(event) {
                                                        var clickedUrl = $(this).data("url");

                                                        //middle click
                                                        if(event.button != 0) {
chrome.tabs.create({url:clickedUrl, selected: localStorage["middle"] == "foreground"});
}
event.preventDefault();
                                                        return false;
})
.click(function(event) {
var clickedUrl = $(this).data("url");

chrome.tabs.getSelected(null, function(tab){
chrome.tabs.update(tab.id, {url:clickedUrl});
window.close();
});
return false;
});

                if(style == "double_title_url") {
                        var $title = $("<div/>", {class:"title", text: title});
                        var $subtitle = $("<div/>", {class:"subtitle", text: url});

                        $info.append($title);
                        $info.append($subtitle);
                } else if(style == "double_url_title") {
                        var $title = $("<div/>", {class:"title", text: url});
                        var $subtitle = $("<div/>", {class:"subtitle", text: title});

                        $info.append($title);
                        $info.append($subtitle);
                } else if(style == "inline_title_url") {
                        var $title = $("<div/>", {class:"title", text: title + " "});
                        var $subtitle = $("<div/>", {class:"subtitle", text: url});

                        $info.append($title);
                        $info.append($subtitle);
                } else if(style == "inline_url_title") {
                        var $title = $("<div/>", {class:"title", text: url});
                        var $subtitle = $("<div/>", {class:"subtitle", text: " " + title});

                        $info.append($title);
                        $info.append($subtitle);
                } else if(style == "inline_title") {
                        var $title = $("<div/>", {class:"title", text: title});
                        $info.attr("title", url);

                        $info.append($title);
                } else if(style == "inline_url") {
                        var $title = $("<div/>", {class:"title", text: url});
                        $info.attr("title", title);

                        $info.append($title);
                }

                $details.append($info);
                $links.append($details);
        }
        $("body").append($links);
}

function setStyling() {
        $("body").width(localStorage["width"]);
        $("body").css("background-color", localStorage["background_color"]);
        $(".title").css("color", localStorage["primary_color"]);
        $(".remove").css("color", localStorage["primary_color"]);
        $(".subtitle").css("color", localStorage["secondary_color"]);
        $(".links .details").css("border-bottom", "1px solid "+ localStorage["border_color"]);
        $(".links .details:last-child").css("border-bottom", "none");

        $(".details").hover(function () {
                $(this).css("background-color", localStorage["hover_color"]);
                $(this).find(".remove").show();
        }, function () {
                $(this).css("background-color", localStorage["background_color"]);
                $(this).find(".remove").hide();
        });
}

function removeUrl(el) {
        var url = el.data("url").toLowerCase();

        //remove from list
        var oldHeight = $("body").height();
        $("body").height(oldHeight - el.parent().outerHeight(true));
        $("html").height(oldHeight - el.parent().outerHeight(true));

        el.parent().hide();

        //add to ignore list
        var ignoreList = JSON.parse(localStorage["ignore"]);
        if(ignoreList.indexOf(url) == -1) {
                ignoreList.push(url);
                localStorage["ignore"] = JSON.stringify(ignoreList);

                //refresh history
                chrome.extension.getBackgroundPage().readHistoryAndMergeIn();
        }

        return false;
}

