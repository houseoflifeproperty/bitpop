var cache = {
  options: {
    history: []
  }
};

function init() {
  initDefaultOptions();
  loadOptionsIntoCache();

  //first start
  chrome.tabs.getAllInWindow(null, function(tabs) {
    for(var i=0;i<tabs.length;i++) {
      chrome.pageAction.show(tabs[i].id);
    }
  });

  chrome.tabs.onUpdated.addListener(function(tabId, changeInfo, tab) {
    if(changeInfo.status == "loading") {
      chrome.pageAction.show(tabId);
    }
  });

  readHistoryAndMergeIn();
  setInterval(function() {
    readHistoryAndMergeIn();
	}, 5*60*1000);
}

function initDefaultOptions() {
  //default options
  if(!localStorage["list_style"]) {
    localStorage["list_style"] = "double_title_url";
  }

  if(!localStorage["show_protocol"]) {
    localStorage["show_protocol"] = "no";
  }

  if(!localStorage["typed_only"]) {
    localStorage["typed_only"] = "yes";
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
}

function saveOptionsToCache(options) {
  cache.options = options;
}

function saveOptionsToDataStore() {
  cache.options.timestamp = Date.now();
  for (option in cache.options) {
    if (option === 'history') {
      try {
        localStorage[option] = JSON.stringify(cache.options[option]);
      }
      catch(e) {
        console.log(e);
      }
    }
    else
      localStorage[option] = cache.options[option];
  }
}

function saveOptionsToCacheAndDataStore(options) {
  saveOptionsToCache(options);
  saveOptionsToDataStore();
  readHistoryAndMergeIn();
}

function loadOptionsIntoCache() {
  if (localStorage['history'])
    cache.options.history = JSON.parse(localStorage['history']);
}

function processHistoryItems(items, startIndex, history, ignoreList, onFinished) {
  var index = startIndex;
  while (index < items.length) {
    if (history.length < localStorage["link_num"] && index < items.length) {
      if (ignoreList.indexOf(items[index].url.toLowerCase()) == -1) {
        if(localStorage["typed_only"] == "no" || (localStorage["typed_only"] == "yes" && items[index].typedCount > 0)) {
          history.push(items[index]);
        }
        else if (localStorage["typed_only"] == "yes" && items[index].typedCount == 0) {
          chrome.history.getVisits({ url: items[index].url }, function (results) {
            for (var counter in results) {
              if (results[counter].transition == 'typed') {
                history.push(items[index]);
                break;
              }
            }
            processHistoryItems(items, index+1, history, ignoreList, onFinished);
          });
          return;
        }
      }
    }
    else {
      break;
    }

    index++;
  }
  onFinished();
}

function readHistoryAndMergeIn() {
  chrome.history.search(
    {
      text: "",
      startTime:(new Date()).getTime()-30*24*3600*1000,
      endTime: (new Date()).getTime(),
      maxResults:0
    },
    function(items) {
      items.sort(function(a,b){return b.visitCount - a.visitCount;});

      var history = new Array();
      var ignoreList = JSON.parse(localStorage["ignore"]);

      processHistoryItems(items, 0, history, ignoreList, function () {
        mergeHistory(history);
        saveOptionsToDataStore();
      });
    }
  );
}

function mergeHistory(newHistory) {
  if (cache.options.history.length == 0) {
    for (var i = 0; i < newHistory.length; i++) {
      cache.options.history.push({
        url: newHistory[i].url,
        visitCount: newHistory[i].visitCount,
        title: newHistory[i].title
      });
    }
    return;
  }

  var res = [];
  var j = 0;
  for (var i = 0; i < cache.options.history.length; i++) {
    while (newHistory[j] >= cache.options.history[i]) {
      res.push({
        url: newHistory[j].url,
        visitCount: newHistory[j].visitCount,
        title: newHistory[j].title
      });
      j++;
    }

    res.push(cache.options.history[i]);
  }

  // now remove duplicates and truncate the resulting array
  var res2 = [];
  o:for (var i = 0; i < res.length; i++) {
    for (j = 0; j < res2.length; j++) {
      if (res[i].url.toLowerCase() == res2[j].url.toLowerCase())
        continue o;
    }
    res2.push(res[i]);
    if (res2.length == localStorage['link_num'])
      break;
  }

  cache.options.history = res2;
}

function mergeOptionsAndSave(options) {
  if (options != cache.options) {
    for (option in options) {
      if (option == 'history') {
        mergeHistory(options[option]);
      }
      else {
        cache.options[option] = options[option];
      }
    }
  }
  saveOptionsToDataStore();
  return cache.options;
}

/**
  * Initialize the background page
  */
window.addEventListener('load', function() {
  init();
});
