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

// date formatting extension
Date.prototype.shortLongFormat = function (timeOnly) {
  var months = [ 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug',
      'Sep', 'Oct', 'Nov', 'Dec'];

  var curr_date = this.getDate();
  var curr_month = this.getMonth();
  curr_month++;
  var curr_year = this.getFullYear();

  var curr_hour = this.getHours();

  var a_p;
  if (curr_hour < 12)
     {
     a_p = "AM";
     }
  else
     {
     a_p = "PM";
     }
  if (curr_hour == 0)
     {
     curr_hour = 12;
     }
  if (curr_hour > 12)
     {
     curr_hour = curr_hour - 12;
     }

  var curr_min = this.getMinutes();
  if (curr_min.toString().length == 1)
    curr_min = '0' + curr_min.toString();

  return timeOnly ? curr_hour + ':' + curr_min + ' ' + a_p :
      months[curr_month - 1] + ' ' + curr_date + ', ' + curr_year + ' at ' +
      curr_hour + ':' + curr_min + ' ' + a_p;
};

Date.prototype.isTodayDate = function() {
  var now = new Date();
  return (this.getDate() == now.getDate()) &&
    (this.getMonth() == now.getMonth()) &&
    (this.getFullYear() == now.getFullYear());
};