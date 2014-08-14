var g_rmJewelAndChatInitialized = false;
var g_titleJustChanged = false; // to prevent recursion when setting title
var g_previousDocumentTitle = "Facebook";
var g_fbJewelsEnabled = true;

/**
 * The height of the pagelet_ticker/chat element when facebook.com is loaded.
 * We save it so that we can restore the element when chat suppression is
 * turned off.
 */
var g_pageletTickerSavedHeight = "50%";
var g_fbChatSidebarBodyHeight = "50%";
var g_pageletTickerFullHeight = "100%";
var g_rescheduleDisableChatCounter = 0;

var port;

// Attempt to reconnect
var reconnectToExtension = function () {
    // Reset port
    port = null;
    // Attempt to reconnect after 1 second
    setTimeout(connectToExtension, 1000 * 1);
};

// Attempt to connect
var connectToExtension = function () {

    // Make the connection
    port = chrome.extension.connect({name: "my-port"});
    if (!port)
        reconnectToExtension();

    // When extension is upgraded or disabled and renabled, the content scripts
    // will still be injected, so we have to reconnect them.
    // We listen for an onDisconnect event, and then wait for a second before
    // trying to connect again. Becuase chrome.extension.connect fires an onDisconnect
    // event if it does not connect, an unsuccessful connection should trigger
    // another attempt, 1 second later.
    port.onDisconnect.addListener(reconnectToExtension);

};

function onPrefsChanged(request) {
    console.log("Prefs changed");
    shouldEnableFbJewelsAndChat_();
}

function init( )
{
    // Connect for the first time
    connectToExtension();

    var tagName = 'g_rmInjected__';
    var injected = document.getElementById(tagName);
    if(!injected)
    {
        saveTickerAndChatHeight();
        injected = document.createElement(tagName);
        injected.id = tagName;
        document.body.appendChild(injected);
        port.onMessage.addListener(onPrefsChanged);
        injectRmJavasctipt();
        console.log("Script injection done");
    }
}

/**
 * Save the height of the element 'pagelet_ticker'/chat.
 * When chat is enabled the height will be restored the last saved height.
 */
function saveTickerAndChatHeight( )
{
    // save the height of pagelet_ticker element when page is initially loaded
    var pagelet_ticker = document.getElementById('pagelet_ticker');
    if(pagelet_ticker)
    {
        g_pageletTickerSavedHeight = pagelet_ticker.style.height;
    }
    var fbChatSidebarBody = document.getElementsByClassName('fbChatSidebarBody');
    if(fbChatSidebarBody.length > 0) {
        g_fbChatSidebarBodyHeight = fbChatSidebarBody[0].style.height;
    }
}

/**
 * Handle response from background page.
 */
function handleBackgroundPageResponse(responseData)
{
    // response from the background page
    var handled = false;
    if('action' in responseData) {
        if(responseData['action'] == 'shouldEnableFbJewelsAndChat') {
            handled = true;
            var enableChat = true;
            var enableJewels = true;
            try {
                if(responseData.response) {
                    if(responseData.response['enableChat'] === false) {
                        enableChat = false;
                    }
                    if(responseData.response['enableJewels'] === false) {
                        enableJewels = false;
                    }
                }
            } catch(e) {
                console.log("Error while setting chat/jewels", e);
            }
            enableChat ? enableFbChat() : disableFbChat();
            enableJewels ? enableFbJewels() : disableFbJewels();
        }
    }
    if(!handled) {
        // event to web page from content script
        var rmResponseEvent = document.createEvent("TextEvent");
        rmResponseEvent.initTextEvent("rmResponseEvent",
                                      false,
                                      false,
                                      null,
                                      JSON.stringify(responseData));
    }
    port.onMessage.removeListener(handleBackgroundPageResponse);
    port.onMessage.addListener(onPrefsChanged);
}

/**
 * listens to events from the web page.
 * Lives in content script.
 */
function listenToRequestsFromWebPage( )
{
    document.addEventListener("rmRequestEvent",
        function(req) {
            if(req && req.data) {
                //send the request to the background page
                port.onMessage.removeListener(onPrefsChanged);
                port.onMessage.addListener(handleBackgroundPageResponse);
                port.postMessage(req.data);
            } else {
                var msg = "Could not send request.  req=" + req;
                var e = document.createEvent("TextEvent");
                e.initTextEvent("rmResponseEvent", false, false, null, JSON.stringify(msg));
                document.dispatchEvent(e);
            }
        }, false
    );
    initJewelAndChatSuppress_( );
    shouldEnableFbJewelsAndChat_( );
}

/**
 * Opens a native chat window.
 * Lives in the web page.
*/
function openChatWindow_(params)
{
    var data = {
                    'id'    : Date.now(),
                    'action': 'chat',
                    'friendId': params
                };
    var e = document.createEvent("TextEvent");
    e.initTextEvent("rmRequestEvent", false, false, null, JSON.stringify(data));
    document.dispatchEvent(e);
}

/**
 * Enable jewels by via css.
 * Lives in content script
*/
function enableFbJewels( )
{
    g_fbJewelsEnabled = true;
    document.body.classList.add('rmJewel');
    var jewelContainer = document.getElementsByTagName('html')[0];
    if(jewelContainer) {
        jewelContainer.classList.add('rmJewel');
    }
    console.log("Enabling FB jewel");
}

/**
 * Disable jewels via css.
 * Lives in content script.
*/
function disableFbJewels( )
{
    g_fbJewelsEnabled = false;
    document.body.classList.remove('rmJewel');
    var jewelContainer = document.getElementsByTagName('html')[0];
    if(jewelContainer) {
        jewelContainer.classList.remove('rmJewel');
    }
    console.log("Disabling FB jewel");
    changeDocumentTitle();
}

/**
 * Enable chat by via css.
 * Lives in content script
*/
function enableFbChat( )
{
    document.body.classList.add('rmChat');
    var dockChat = document.getElementsByTagName('html')[0];
    g_rescheduleDisableChatCounter = 0;
    if(dockChat) {
        dockChat.classList.add('rmChat');
    }
    // restore the height of the ticker/chat so that chat shows up.
    var msg = "";
    var pagelet_ticker = document.getElementById('pagelet_ticker');
    var fbChatSidebarBody = document.getElementsByClassName('fbChatSidebarBody');

    if(pagelet_ticker) {
        pagelet_ticker.style.height = g_pageletTickerSavedHeight;
        msg += " TickerHeight=" + pagelet_ticker.style.height;
        if(fbChatSidebarBody.length > 0) {
            fbChatSidebarBody[0].style.height = g_fbChatSidebarBodyHeight;
            msg += " ChatHeight=" + fbChatSidebarBody[0].style.height;
        }
    }
    console.log("Enabling FB chat. " + msg);
}

/**
 * Disable chat via css.
 * Lives in content script.
*/
function disableFbChat( )
{
    var shouldReschedule = false;
    document.body.classList.remove('rmChat');
    var dockChat = document.getElementsByTagName('html')[0];
    if(dockChat) {
        dockChat.classList.remove('rmChat');
    }
    // make the ticker full height when disabling chat
    var pagelet_ticker = document.getElementById('pagelet_ticker');
    var msg = "";
    if(pagelet_ticker) {
        saveTickerAndChatHeight();
        pagelet_ticker.style.height = g_pageletTickerFullHeight;
        msg += " TickerHeight=" + pagelet_ticker.style.height;
        var fbChatSidebarBody = document.getElementsByClassName('fbChatSidebarBody');
        if(fbChatSidebarBody.length > 0) {
            fbChatSidebarBody[0].style.height = "0px";
            msg += " ChatHeight=" + fbChatSidebarBody[0].style.height
        } else {
            shouldReschedule = true;
        }
    } else {
        shouldReschedule = true;
    }
    console.log("Disabling FB chat. " + msg);
    if(shouldReschedule && g_rescheduleDisableChatCounter < 3) {
        ++g_rescheduleDisableChatCounter;
        console.log("Rescheduling disabling chat. " + g_rescheduleDisableChatCounter);
        setTimeout(disableFbChat,500);
    }
}

/**
 * Initialize the FB Jewel/Chat suppression by injecting the css
 * Lives in the content script.
 */
function initJewelAndChatSuppress_( )
{
    if(!g_rmJewelAndChatInitialized)
    {
        g_rmJewelAndChatInitialized = true;
        var styleElement = document.createElement("style");
        styleElement.type = "text/css";
        styleElement.appendChild(
            document.createTextNode(
                "#jewelCase {display: none; visibility: hidden;}\n" +
                "#jewelContainer {display: none; visibility: hidden;}" +
                ".fbNubGroup {display: none ;visibility: hidden;}" +
                ".fbChatSidebarBody {display: none ;visibility: hidden; }" +
                ".fbChatSidebarFooter {display: none ;visibility: hidden; }" +
                "#fbDockChatBuddylistNub { visibility:hidden; display:none; }" +
                ".rmJewel #jewelCase { visibility: visible !important; display: block !important;} " +
                ".rmJewel #jewelContainer {visibility: visible !important;display: block !important;}"+
                ".rmChat .fbNubGroup {visibility: visible !important;display: block !important;}" +
                ".rmChat #fbNubGroup {visibility: visible !important;display: block !important;}" +
                ".rmChat .fbChatSidebarBody {visibility: visible !important;display: block !important;}" +
                ".rmChat .fbChatSidebarFooter {visibility: visible !important;display: block !important;}" +
                ".rmChat #fbDockChatBuddylistNub { visibility: visible !important; display: block !important; }"
                ));
        document.body.appendChild(styleElement);
    }
}

/**
 * send an event to content script to check if jewels/chat should be enabled.
 * Lives in the content script.
 */
function shouldEnableFbJewelsAndChat_( )
{
    var parts = document.cookie.match(/c_user=(\d+)/i);
    var userId = (parts != null && parts.length > 1? parts[1] : "");
    var data = {
                'id': Date.now(),
                'action': 'shouldEnableFbJewelsAndChat',
                'userId': userId
            };
    // send the event
    var e = document.createEvent("TextEvent");
    e.initTextEvent("rmRequestEvent", false, false, null, JSON.stringify(data));
    document.dispatchEvent(e);
}

/**
 * Listen to events from content script.
 * Lives in the web page.
 */
function listenToRmResponse_(e)
{
}

/**
 * Injects javascript event under the 'External.Chat' namespace which FB
 * can call to trigger the 'rmChatEventRequest'.
 * Lives in the content script.
 */
function injectRmJavasctipt() {
    // add a script element to the document body
    var newScript = document.createElement('script');
    newScript.type = 'text/javascript';
    var jsSrc = document.createTextNode(
            'var External = ' +
                '{' +
                    'listenToRmResponse: ' + listenToRmResponse_.toString() + ',\n' +
                    'Chat: { \n' +
                        'openWindow :  ' + openChatWindow_.toString() + ',\n' +
                        'dummy: " "\n' +
                    '}\n' +
                '}; ' +
                'document.addEventListener("rmResponseEvent", External.listenToRmResponse);\n' +
                ''
            );
    newScript.appendChild(jsSrc);
    listenToRequestsFromWebPage();
    setupDocumentTitleChangeListener();
    document.body.appendChild(newScript);
}

/**
 * Change the document title
 * 1. change to previous if title is set to '<user> messaged you'
 * 2. remove trailing pattern '(<number>)'
 */
function changeDocumentTitle( ) {
    var oldTitle = document.title;
    var newTitle = oldTitle;
    if(g_titleJustChanged) {
        // prevent recursion when this function is changing the title
        g_titleJustChanged = false;
        g_previousDocumentTitle = document.title;
    } else {
        if(!g_fbJewelsEnabled) {
            if(document.title.search("messaged you$") > 0) {
                // if the title ends with "<user> messaged you!" then restore
                // the previous title and mark as changed to prevent infinite recursion
                g_titleJustChanged = true;
                newTitle = g_previousDocumentTitle;
            } else {
                if(document.title.search(/\(\d+\) /) >= 0) {
                    // this is the ' Facebook (1)' case
                    g_titleJustChanged = true;
                    newTitle = document.title.replace(/\(\d+\) /, "");
                }
            }
        }
    }
    if(g_titleJustChanged)
    {
        console.log("Title changed. Time=", Date.now(),
                    ", Old=", oldTitle,
                    ", New=", newTitle);
        document.title = newTitle;
    }
}

function setupDocumentTitleChangeListener() {
    // event listening to tittle change event.
    var titleEl = document.getElementsByTagName("title")[0];
    titleEl.addEventListener("DOMSubtreeModified", function(evt) {
        changeDocumentTitle();
        }, false);
    changeDocumentTitle();  // fix the title at startup.
}

init();
