JAVASCRIPT = '''
// <;![Cdata[
//
// Cookie functions
//

// Creates a new cookie.
function createCookie(name, value, day) {
    var date = new Date();
    date.setTime(date.getTime() + (day * 24 * 60 * 60 * 1000));
    var expires = "; expires=" + date.toGMTString();
    document.cookie = name + "=" + value+expires + "; path=/";
}

// Returns the vaue of a cookie, or null if it does not exist.
function readCookie(name) {
    var begin = name + "=";
    var data = document.cookie.split(';');
    for(var i = 0; i < data.length; i++) {
        var cookie = data[i];
        while (cookie.charAt(0) == ' ')
            cookie = cookie.substring(1, cookie.length);
        if (cookie.indexOf(begin) == 0)
            return cookie.substring(begin.length, cookie.length);
    }

    return null;
}

// Deletes a cookie.
function eraseCookie(name) {
    createCookie(name, "", -1);
}

//
// Functions to change the layout of the page.
//

// Hides all "details" and "comments" section.
function collapse() {
    // Hide all Comments sections.
    var comments = document.querySelectorAll('.DevComment');
    for(var i = 0; i < comments.length; i++) {
        comments[i].style.display = "none";
    }

    // Hide all details sections.
    var details = document.querySelectorAll('.DevDetails');
    for(var i = 0; i < details.length; i++) {
        details[i].style.display = "none";
    }

    // Fix the rounding on the Revision box. (Lower right corner must be round)
    var revisions = document.querySelectorAll('.DevRev');
    for(var i = 0; i < revisions.length; i++) {
      revisions[i].className = revisions[i].className + ' DevRevCollapse';
    }

    // Fix the rounding on the last category box. (Lower left corner must be round)
    var status = document.querySelectorAll('.last');
    for(var i = 0; i < status.length; i++) {
        status[i].className = status[i].className + ' DevStatusCollapse';
    }

    // Create a cookie to remember that we want the view to be collapsed.
    createCookie('collapsed', 'true', 30)

    // Hide the collapse and the unmerge buttons.
    document.querySelectorAll('.collapse')[0].style.display = 'none'
    document.querySelectorAll('.unmerge')[0].style.display = 'none'

    // Activate the merge and expand buttons.
    document.querySelectorAll('.expand')[0].style.display = 'inline'
    document.querySelectorAll('.merge')[0].style.display = 'inline'
}

// Expands the view. This is the opposite of "Collapse"
function expand() {
    // Make the comments visible.
    var comments = document.querySelectorAll('.DevComment');
    for(var i = 0; i < comments.length; i++) {
        comments[i].style.display = "";
    }

    // Make the details visible.
    var details = document.querySelectorAll('.DevDetails');
    for(var i = 0; i < details.length; i++) {
        details[i].style.display = "";
    }

    // Remove the round corner (lower right) for the Revision box.
    var revisions = document.querySelectorAll('.DevRev');
    for(var i = 0; i < revisions.length; i++) {
        revisions[i].className = revisions[i].className.replace('DevRevCollapse', '');
    }

    // Remoe the round corner (lower left) for the last category box.
    var status = document.querySelectorAll('.DevStatus');
    for(var i = 0; i < status.length; i++) {
        status[i].className = status[i].className.replace('DevStatusCollapse', '');
    }

    // Delete the cookies that say that we want to be collapsed or merged.
    eraseCookie('collapsed')
    eraseCookie('merged')

    // Display the "collapse" and "merge" buttons.
    document.querySelectorAll('.collapse')[0].style.display = 'inline'
    document.querySelectorAll('.merge')[0].style.display = 'inline'

    // Remove the "expand" and "unmerge" buttons.
    document.querySelectorAll('.expand')[0].style.display = 'none'
    document.querySelectorAll('.unmerge')[0].style.display = 'none'
}

//
// Merge all the status boxes together.
function merge() {
    // First step is to collapse the view.
    collapse();

    // Hide all the spacing.
    var spacing = document.querySelectorAll('.DevStatusSpacing');
    for(var i = 0; i < spacing.length; i++) {
        spacing[i].style.display = "none";
    }

    // Each boxes have, in the className, a tag that uniquely represents the
    // build where this data comes from.
    // Since we  want to merge all the boxes coming from the same build, we
    // parse the document to find all the builds, and then, for each build, we
    // concatenate the boxes.

    var allTags = [];
    all = document.getElementsByTagName('*')
    for(var i = 0; i < all.length; i++) {
        var element = all[i];
        start = element.className.indexOf('Tag')
        if (start != -1) {
            var className = ""
            end = element.className.indexOf(' ', start)
            if (end != -1) {
                className = element.className.substring(start, end);
            } else {
                className = element.className.substring(start);
            }
            allTags[className] = 1;
        }
    }

    // Mergeall tags that we found
    for (i in allTags) {
        var current = document.querySelectorAll('.' + i);

        // We do the work only if there is more than 1 box with the same
        // build.
        if (current.length > 1) {
            // Add the noround class to all the boxes.
            for(var i = 0; i < current.length; i++) {
                current[i].className = current[i].className + ' noround';
            }

            // Add the begin class to the first box.
            current[0].className = current[0].className + ' begin';

            // Add the end class to the last box.
            last = current.length - 1;
            current[last].className = current[last].className + ' end';
        }
    }

    // Display the "unmerge" and "expand" button.
    // TODO(nsylvain): expand does not work well here. we should remove it.
    document.querySelectorAll('.unmerge')[0].style.display = 'inline'
    document.querySelectorAll('.expand')[0].style.display = 'inline'

    // Remove the "collapse" and "merge" button.
    document.querySelectorAll('.collapse')[0].style.display = 'none'
    document.querySelectorAll('.merge')[0].style.display = 'none'

    // Create a cookie to remember that we want to be merged.
    createCookie('merged', 'true', 30)
}

// Un-merge the view. This is the opposite of "merge".
function unmerge() {
    // We start by expanding the view.
    expand();

    // We put back all the spacing.
    var spacing = document.querySelectorAll('.DevStatusSpacing');
    for(var i = 0; i < spacing.length; i++) {
        spacing[i].style.display = "";
    }

    // We remove the class added to all the boxes we modified.
    var noround = document.querySelectorAll('.noround');
    for(var i = 0; i < noround.length; i++) {
        noround[i].className = noround[i].className.replace("begin", '');
        noround[i].className = noround[i].className.replace("end", '');
        noround[i].className = noround[i].className.replace("noround", '');
    }

    // Delete the cookie, we don't want to be merged anymore.
    eraseCookie('merged')

    // Display the "merge" and "collapse" button.
    document.querySelectorAll('.collapse')[0].style.display = 'inline'
    document.querySelectorAll('.merge')[0].style.display = 'inline'

    // Hide and "expand" and "unmerge" button.
    document.querySelectorAll('.expand')[0].style.display = 'none'
    document.querySelectorAll('.unmerge')[0].style.display = 'none'
}

function SetupView() {
    if (readCookie('merged')) {
        merge();
    } else if (readCookie('collapsed')) {
        collapse();
    } else  {
        unmerge();
        expand();
    }
}

//
// Functions used to display the build status bubble on box click.
//

// show the build status box. This is called when the user clicks on a block.
function showBuildBox(url, event) {
    //  Find the current curson position.
    var cursorPosTop = (window.event ? window.event.clientY : event.pageY)
    var cursorPosLeft = (window.event ? window.event.clientX : event.pageX)

    // Offset the position by 5, to make the window appears under the cursor.
    cursorPosTop  = cursorPosTop  + document.body.scrollTop -5 ;
    cursorPosLeft = cursorPosLeft  + document.body.scrollLeft - 5;

    // Move the div (hidden) under the cursor.
    var divBox = document.getElementById('divBox');
    divBox.style.top = parseInt(cursorPosTop) + 'px';
    divBox.style.left = parseInt(cursorPosLeft) + 'px';

    // Reload the hidden frame with the build page we want to show.
    // The onload even on this frame will update the div and make it visible.
    document.getElementById("frameBox").src = url

    // We don't want to reload the page.
    return false;
}

// OnLoad handler for the iframe containing the build to show.
function updateDiv(event) {
    // Get the frame innerHTML.
    var iframeContent = document.getElementById("frameBox").contentWindow.document.body.innerHTML;

    // If there is any content, update the div, and make it visible.
    if (iframeContent) {
        var divBox = document.getElementById('divBox');
        divBox.innerHTML = iframeContent ;
        divBox.style.display = "block";
    }
}

// Util functions to know if an element is contained inside another element.
// We use this to know when we mouse out our build status div.
function containsDOM (container, containee) {
    var isParent = false;
    do {
        if ((isParent = container == containee))
            break;
        containee = containee.parentNode;
    } while (containee != null);

    return isParent;
}

// OnMouseOut handler. Returns true if the mouse moved out of the element.
// It is false if the mouse is still in the element, but in a blank part of it,
// like in an empty table cell.
function checkMouseLeave(element, event) {
  if (element.contains && event.toElement) {
    return !element.contains(event.toElement);
  }
  else if (event.relatedTarget) {
    return !containsDOM(element, event.relatedTarget);
  }
}

function addBox(url, title, color, tag) {
  document.write('<td class="DevStatusBox">')
  document.write('<a href="#" onClick="showBuildBox(\\\'')
  document.write(url);
  document.write('\\\', event); return false;\" title="');
  document.write(title);
  document.write('" class="DevStatusBox ');
  document.write(color + ' ' + tag);
  document.write('" target=_blank></a></td>');
}

document.addEventListener("DOMContentLoaded", SetupView, false);

// ]]>
'''
