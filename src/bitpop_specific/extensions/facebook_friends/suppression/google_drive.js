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

setTimeout(function() {

	var removeBar = function() {
		var shownBars = document.getElementsByClassName('jfk-butterBar jfk-butterBar-shown jfk-butterBar-info');
		for (var i = 0; i < shownBars.length; i++) {
			if (shownBars[i].innerText && shownBars[i].innerText.indexOf("Google Chrome") != -1) {
				shownBars[i].parentNode.removeChild(shownBars[i]);
				KX_resize();
			}
		}
	};

	removeBar();
	setIinterval(removeBar, 2000);
}, 500);
