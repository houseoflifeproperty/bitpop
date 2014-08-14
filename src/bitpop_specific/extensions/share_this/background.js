// BitPop browser. Facebook chat integration part.
// Copyright (C) 2014 BitPop AS
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

(function () {
  /**
   * Returns a handler which will open a new window when activated.
   */
       
  function getClickHandler() {
    return function(info, tab) {
      // The srcUrl property is only available for image elements.
        
      var url = 'https://tools.bitpop.com/fbimage.html?url=' + encodeURIComponent(info.srcUrl) + "&ref=CEX";
      var w = 470;
      var h = 520;
      var left = Math.floor((screen.width/2)-(w/2));
      var top = Math.floor((screen.height/2)-(h/2)); 
      chrome.windows.create({url: url, type: 'popup', width: w, height:h, top: top, left: left });
    };
  }


  /**
  * Create a context menu which will only show up for images.
  */
  chrome.contextMenus.create({
    "title" : "Share this image on Facebook",
    "type" : "normal",
    "contexts" : ["image"],
    "onclick" : getClickHandler()
  });
})();
