(function($) {
  var regEx = /((((http|https|ftp):\/\/)|(www\.))[\u007F-\uFFFF-a-zA-Z0-9\-\_]+(?![(\u007F-\uFFFF|\w)\s?&.\{\}\/;#~%'"=-]*>)(\.[\u007F-\uFFFF-a-zA-Z0-9\-]+)*(\.[\u007F-\uFFFF-a-zA-Z]{2,})?(:\d+)?([\/#][(\u007F-\uFFFF|\w)?\{\}\(\)=&.\/\-;,#~%$:'+!@\*]*)?)/gi;
  $.autolink = function (input, o) {
    var defaults = {
      truncation_length: 20,
      truncation_omission: "..."
    };
    var skipped_attrs = [ 'truncation_length',
    											'truncation_omission',
    											'href',
    											'title'
    										];
    var options = $.extend({}, defaults, o);
    return input.replace(regEx, function(matches) {
      // Determine if there is punctuation trailing the link and store it for use outside the anchor tag
      // There is probably a method that behaves better with the overlap of punctuation characters in the white list of Path characters.
      var punctuation = '';

      matches = matches.replace(/[\,\.\!\?\(\)]+$/ig,function(matchPunctuation){
        if (matchPunctuation) {
          punctuation = matchPunctuation;
        }
        return '';
      });
      var linkDisplay = matches;
      var title = '';
      // if (matches.length >= options.truncation_length) {
      //   linkDisplay = matches.substring(0,(options.truncation_length + 1)) + options.truncation_omission;
      //   title = ' title="' + matches + '"';
      // }

      var attrs = '';
      for (var opt in options) {
      	if (options.hasOwnProperty(opt) && skipped_attrs.indexOf(opt) == -1) {
      		attrs += ' ' + opt + '="' + options[opt] + '"';
      	}
      }

      var prefix = '';
      if (!matches.match(/^((http|https|ftp):\/\/)/i)) {
        prefix = 'http://';
      }

      return ['<a href="', prefix, matches, '"', title, attrs, '>', linkDisplay, '</a>', punctuation].join('');
    });
  };
})(jQuery);
